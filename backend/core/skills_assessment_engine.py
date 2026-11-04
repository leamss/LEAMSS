"""Skills Assessment Intelligence Engine (Phase 21).

Implements official guidelines from:
  1. ACS (Australian Computer Society):
     - IT Major: Bachelor+ >= 33% IT units, 2-yr Master's/Postgrad >= 50% IT units, Diploma >= 1 academic year IT.
     - Closely Related: >= 65% of IT units match the nominated ANZSCO code.
     - IT Minor: IT content >= 2/3 of Major requirement.
     - Non-IT / Insufficient IT: requires RPL (Recognition of Prior Learning) with 6 years experience + 2 project reports.
     - Experience deductions (Requirement Met Date):
       • Bachelor+ IT Major Closely Related: 2 years in last 10 yrs (or 4 yrs anytime).
       • Bachelor+ IT Major NOT Closely Related: 4 years anytime.
       • Bachelor+ IT Minor Closely Related: 5 years in last 10 yrs (or 6 yrs anytime).
       • Bachelor+ IT Minor NOT Closely Related: 6 years anytime.
       • Diploma IT Major Closely Related: 5 years in last 10 yrs (or 6 yrs anytime).
       • Diploma IT Major NOT Closely Related: 6 years anytime.
       • Non-IT / Insufficient (RPL Pathway): 6 years required & deducted.

  2. VETASSESS Professional Occupations (Groups A, B, C, D, E, F):
     - Group A: AQF Bachelor+ in highly relevant field. 1 yr post-qualification paid employment (20+ hrs/wk) in last 5 yrs. Pre-qual does NOT apply. (Deduction: 1 yr).
     - Group B: AQF Bachelor+.
       • Pathway 1 (Highly relevant major): 1 yr post-qual in last 5 yrs (Deduction: 1 yr).
       • Pathway 2 (Non-relevant major + AQF Diploma in relevant field): 2 yrs post-qual in last 5 yrs (Deduction: 2 yrs).
       • Pathway 3 (Non-relevant major): 3 yrs post-qual in last 5 yrs (Deduction: 3 yrs).
       • Pathway 4 (Pre-qualification): 5 yrs pre-qual relevant employment + 1 yr post-qual in last 5 yrs (Deduction: 5 yrs).
     - Group C: AQF Diploma+.
       • Pathway 1 (Highly relevant Diploma): 1 yr post-qual in last 5 yrs (Deduction: 1 yr).
       • Pathway 2 (Non-relevant Diploma + Cert IV in relevant field): 2 yrs post-qual in last 5 yrs (Deduction: 2 yrs).
       • Pathway 3 (Non-relevant Diploma): 2 yrs post-qual in last 5 yrs (Deduction: 2 yrs).
       • Pathway 4 (Pre-qualification): 3 yrs pre-qual + 1 yr in last 5 yrs (Deduction: 3 yrs).
     - Group D: AQF Certificate III/IV+.
       • Pathway 1 (Cert IV relevant major): 1 yr post-qual (Deduction: 1 yr).
       • Pathway 2 (Cert IV non-relevant major): 2 yrs post-qual (Deduction: 2 yrs).
       • Pathway 3 (Cert III relevant major): 3 yrs post-qual (Deduction: 3 yrs).
       • Pathway 4 (Pre-qualification): 3 yrs pre-qual + 1 yr in last 5 yrs (Deduction: 3 yrs).
     - Group E: AQF Advanced Diploma/Associate Degree in highly relevant field. 1 yr post-qual in last 5 yrs. Pre-qual does NOT apply. (Deduction: 1 yr).
     - Group F: AQF Certificate II/III+. 1 yr post-qual (relevant major), 2 yrs (non-relevant), or 4 yrs pre-qual.

  3. TRA and VETASSESS Trade Occupations (TRA-approved RTO):
     - Licensed trade, no formal training: 6 years experience (Deduction: 6 yrs).
     - Licensed trade, relevant formal training: 4 years experience (Deduction: 4 yrs).
     - Non-licensed trade, no formal training: 5 years experience (Deduction: 5 yrs).
     - Non-licensed trade, relevant formal training: 3 years experience (Deduction: 3 yrs).
     - Currency requirement: At least 12 months in nominated occupation within last 3 years.
"""
from typing import Dict, Any, List, Optional, Tuple
import re


def _normalize_str(val: Any) -> str:
    return (str(val) if val is not None else "").strip().lower()


def _to_float(val: Any) -> float:
    try:
        if val is None or val == "":
            return 0.0
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def calculate_gsm_experience_points(claimable_years: float, in_australia: bool = False) -> Tuple[int, str]:
    """Calculate Points under the Australian GSM Points Test (Subclass 189/190/491).
    Overseas Skilled Employment (outside Australia):
      • Less than 3 years: 0 points
      • 3 to 4 years (3 - <5): 5 points
      • 5 to 7 years (5 - <8): 10 points
      • 8 or more years (8+): 15 points
    Australian Skilled Employment (in Australia):
      • Less than 1 year: 0 points
      • 1 to 2 years: 5 points
      • 3 to 4 years: 10 points
      • 5 to 7 years: 15 points
      • 8 or more years: 20 points
    """
    y = float(claimable_years)
    if in_australia:
        if y >= 8.0:
            return 20, "8+ years in Australia (20 pts)"
        elif y >= 5.0:
            return 15, "5-7 years in Australia (15 pts)"
        elif y >= 3.0:
            return 10, "3-4 years in Australia (10 pts)"
        elif y >= 1.0:
            return 5, "1-2 years in Australia (5 pts)"
        return 0, "Less than 1 year in Australia (0 pts)"
    else:
        if y >= 8.0:
            return 15, "8+ years overseas (15 pts)"
        elif y >= 5.0:
            return 10, "5-7 years overseas (10 pts)"
        elif y >= 3.0:
            return 5, "3-4 years overseas (5 pts)"
        return 0, "Less than 3 years points-claimable overseas (0 pts)"


# ══════════════════════════════════════════════════════════════════════════
# QUALIFICATION RELEVANCE EVALUATION ENGINE
# ══════════════════════════════════════════════════════════════════════════
def _has_keyword(text: str, keywords: List[str]) -> bool:
    t = (text or "").lower()
    for kw in keywords:
        kw = kw.strip().lower()
        if not kw:
            continue
        if len(kw) <= 3:
            if re.search(r"\b" + re.escape(kw) + r"\b", t):
                return True
        else:
            if re.search(r"\b" + re.escape(kw), t):
                return True
    return False


def is_field_relevant_to_occupation(field_of_study: str, occ: Dict[str, Any]) -> Tuple[bool, str]:
    """Determine whether candidate's field of study is highly relevant to nominated occupation."""
    f = _normalize_str(field_of_study)
    if not f:
        return True, "No field of study specified; evaluated based on standard criteria."

    code = str(occ.get("code") or "").strip()
    title = _normalize_str(occ.get("title") or "")
    group = _normalize_str((occ.get("hierarchy") or {}).get("unit_group_name") or occ.get("group") or "")

    # 1. ICT / Computing (ANZSCO 1351, 261x, 262x, 2631, 2632, 313x)
    is_ict_occ = (
        code.startswith("261") or code.startswith("262") or code in ("263111", "263211", "263212", "263213", "263299")
        or code.startswith("1351") or code.startswith("313") or "ict" in title or "software" in title or "computer" in title
    )
    ict_keywords = [
        "computer", "computing", "software", "information technology", "information systems",
        "cyber", "data science", "network", "mca", "bca", "msc it", "b.tech cse", "btech cse",
        "btech it", "cloud", "artificial intelligence", "ai"
    ]
    if is_ict_occ:
        is_rel = _has_keyword(f, ict_keywords)
        return is_rel, "Field matches ICT discipline" if is_rel else f"Field '{field_of_study}' is non-ICT"

    # 2. Engineering (ANZSCO 233x, 312x, 2633)
    is_eng_occ = (
        code.startswith("233") or code.startswith("312") or code.startswith("2633")
        or "engineer" in title or "engineering" in group
    )
    eng_keywords = [
        "engineering", "engineer", "mechanical", "civil", "electrical", "electronics",
        "chemical", "mechatronics", "aerospace", "aeronautical", "structural", "mining",
        "petroleum", "biomedical", "telecommunications engineering", "b.tech", "btech", "b.e."
    ]
    if is_eng_occ:
        is_rel = _has_keyword(f, eng_keywords)
        return is_rel, "Field matches engineering discipline" if is_rel else f"Field '{field_of_study}' is not an engineering discipline"

    # 3. Accounting & Finance (ANZSCO 221x, 222x)
    is_acc_occ = (
        code.startswith("2211") or code.startswith("2212") or code.startswith("222")
        or "accountant" in title or "auditor" in title or "financial" in title
    )
    acc_keywords = [
        "account", "accounting", "finance", "commerce", "b.com", "bcom", "m.com", "mcom",
        "audit", "taxation", "ca", "cpa", "cfa", "banking"
    ]
    if is_acc_occ:
        is_rel = _has_keyword(f, acc_keywords)
        return is_rel, "Field matches accounting/finance discipline" if is_rel else f"Field '{field_of_study}' is not accounting/finance"

    # 3b. Actuarial, Mathematics, Statistics & Quantitative Data Science (ANZSCO 2241)
    is_actuarial_occ = (
        code.startswith("2241")
        or any(k in title for k in ["actuary", "mathematician", "statistician"])
    )
    if is_actuarial_occ:
        act_keywords = ["actuarial", "actuary", "mathematics", "mathematical", "statistics", "statistical", "data science", "quantitative"]
        is_rel = _has_keyword(f, act_keywords)
        return is_rel, "Field matches actuarial/mathematics/statistics discipline" if is_rel else f"Field '{field_of_study}' is not actuarial/mathematics/statistics"

    # 3c. Design, Visual & Multimedia Arts (ANZSCO 2324, 2612)
    is_design_occ = (
        code.startswith("2324") or code.startswith("2323") or code.startswith("2325") or code.startswith("2612")
        or any(k in title for k in ["graphic designer", "illustrator", "multimedia designer", "web designer", "ui/ux", "user interface", "visual designer"])
    )
    if is_design_occ:
        design_keywords = ["design", "graphic design", "visual communication", "multimedia", "digital media", "ui", "ux", "fine arts", "animation", "web design"]
        is_rel = _has_keyword(f, design_keywords)
        return is_rel, "Field matches design/multimedia discipline" if is_rel else f"Field '{field_of_study}' is not design/multimedia"

    # 4. Business, Management, Administration, Marketing, PR, HR, Project Administration, Sales
    # (ANZSCO 111x, 131x, 132x, 133x, 141x, 142x, 149x, 223x, 224x, 225x, 511x)
    is_biz_occ = (
        code.startswith("111") or code.startswith("131") or code.startswith("132") or code.startswith("133")
        or code.startswith("141") or code.startswith("142") or code.startswith("149")
        or code.startswith("223") or code.startswith("224") or code.startswith("225") or code.startswith("511")
        or any(k in title for k in ["manager", "management", "consultant", "administrator", "analyst", "organis", "marketing", "business", "policy", "project", "human resource", "recruitment", "sales", "adviser"])
    )
    biz_keywords = [
        "business", "management", "administration", "commerce", "marketing", "finance",
        "human resource", "hr", "operations", "economics", "international business",
        "public administration", "project management", "corporate", "bba", "mba", "organisational",
        "supply chain", "logistics", "strategy", "sales", "recruitment", "talent", "personnel",
        "workplace relations", "industrial relations", "advertising", "public relations"
    ]
    if is_biz_occ:
        is_rel = _has_keyword(f, biz_keywords)
        return is_rel, "Field matches business/management discipline" if is_rel else f"Field '{field_of_study}' is not business/management"

    # 5. Healthcare / Nursing / Medical (ANZSCO 251x, 252x, 253x, 254x, 411x)
    is_health_occ = (
        code.startswith("25") or code.startswith("411")
        or any(k in title for k in ["nurse", "medical", "doctor", "health", "physio", "pharm"])
    )
    health_keywords = [
        "medicine", "medical", "mbbs", "md", "nursing", "midwife", "health",
        "pharmacy", "physiotherapy", "dental", "dentist", "optometry"
    ]
    if is_health_occ:
        is_rel = _has_keyword(f, health_keywords)
        return is_rel, "Field matches healthcare/medical discipline" if is_rel else f"Field '{field_of_study}' is not healthcare/medical"

    # 6. Education & Teaching (ANZSCO 241x)
    is_teach_occ = code.startswith("241") or "teacher" in title or "teaching" in title or "education" in title
    teach_keywords = [
        "education", "teaching", "teach", "b.ed", "bed", "m.ed", "med",
        "early childhood", "primary", "secondary"
    ]
    if is_teach_occ:
        is_rel = _has_keyword(f, teach_keywords)
        return is_rel, "Field matches education/teaching discipline" if is_rel else f"Field '{field_of_study}' is not education/teaching"

    # 7. Architecture & Building (ANZSCO 232x, 1331)
    is_arch_occ = (
        code.startswith("232") or code == "133111"
        or any(k in title for k in ["architect", "landscape", "urban planner", "construction"])
    )
    arch_keywords = ["architecture", "architect", "urban planning", "town planning", "landscape", "construction", "building"]
    if is_arch_occ:
        is_rel = _has_keyword(f, arch_keywords)
        return is_rel, "Field matches architecture/construction discipline" if is_rel else f"Field '{field_of_study}' is not architecture/construction"

    # 8. Science & Environment (ANZSCO 234x)
    is_sci_occ = code.startswith("234") or any(k in title for k in ["scientist", "chemist", "geologist", "biologist", "agronomist"])
    sci_keywords = ["chemistry", "biology", "physics", "geology", "science", "biotechnology", "environment", "agriculture", "agronomy"]
    if is_sci_occ:
        is_rel = _has_keyword(f, sci_keywords)
        return is_rel, "Field matches science discipline" if is_rel else f"Field '{field_of_study}' is not natural/physical science"

    # 9. Legal & Social (ANZSCO 271x, 272x)
    is_law_occ = (
        code.startswith("271") or code.startswith("272")
        or any(k in title for k in ["lawyer", "solicitor", "barrister", "social worker", "psychologist", "counsellor"])
    )
    law_keywords = ["law", "legal", "llb", "llm", "social work", "psychology", "counselling", "welfare"]
    if is_law_occ:
        is_rel = _has_keyword(f, law_keywords)
        return is_rel, "Field matches legal/social discipline" if is_rel else f"Field '{field_of_study}' is not legal/social discipline"

    # 10. Culinary Arts, Commercial Cookery & Hospitality Management (ANZSCO 351x, 141x)
    is_culinary_occ = (
        code.startswith("351") or code in ("141111", "141211", "141311", "141999")
        or any(k in title for k in ["chef", "cook", "baker", "pastry", "culinary", "hospitality", "hotel manager", "restaurant manager", "cafe manager"])
    )
    culinary_keywords = [
        "culinary", "cookery", "commercial cookery", "chef", "cook", "hospitality", "hotel management",
        "catering", "food production", "food technology", "pastry", "baking", "patisserie", "bhm", "hotel", "food and beverage", "gastronomy"
    ]
    if is_culinary_occ:
        is_rel = _has_keyword(f, culinary_keywords)
        return is_rel, "Field matches culinary/hospitality discipline" if is_rel else f"Field '{field_of_study}' is not culinary/hospitality"

    # 11. Automotive Trades (ANZSCO 321x)
    is_auto_occ = (
        code.startswith("321") or any(k in title for k in ["motor mechanic", "diesel mechanic", "motorcycle", "panelbeater", "automotive"])
    )
    auto_keywords = ["automotive", "automobile", "motor vehicle", "diesel", "motor mechanic", "autotronics", "vehicle", "mechanical"]
    if is_auto_occ:
        is_rel = _has_keyword(f, auto_keywords)
        return is_rel, "Field matches automotive discipline" if is_rel else f"Field '{field_of_study}' is not automotive discipline"

    # 12. Electrical & Electronics Trades (ANZSCO 341x, 342x)
    is_elec_trade_occ = (
        code.startswith("341") or code.startswith("342")
        or any(k in title for k in ["electrician", "airconditioning", "refrigeration", "electrical linesworker"])
    )
    elec_trade_keywords = ["electrical", "electrician", "electronics", "air conditioning", "refrigeration", "hvac", "power"]
    if is_elec_trade_occ:
        is_rel = _has_keyword(f, elec_trade_keywords)
        return is_rel, "Field matches electrical trade discipline" if is_rel else f"Field '{field_of_study}' is not electrical trade"

    # 13. Construction, Carpentry & Plumbing Trades (ANZSCO 331x, 332x, 333x, 334x)
    is_const_trade_occ = (
        code.startswith("331") or code.startswith("332") or code.startswith("333") or code.startswith("334")
        or any(k in title for k in ["carpenter", "joiner", "bricklayer", "stonemason", "painter", "glazier", "plasterer", "tiler", "plumber"])
    )
    const_trade_keywords = ["carpentry", "joinery", "construction", "building", "bricklaying", "painting", "plumbing", "plastering", "tiling", "glazing", "civil"]
    if is_const_trade_occ:
        is_rel = _has_keyword(f, const_trade_keywords)
        return is_rel, "Field matches construction/carpentry/plumbing trade discipline" if is_rel else f"Field '{field_of_study}' is not construction/plumbing trade"

    # 14. Fabrication, Engineering Trades & Metal (ANZSCO 322x, 323x)
    is_fab_occ = (
        code.startswith("322") or code.startswith("323")
        or any(k in title for k in ["metal fabricator", "welder", "fitter", "machinist", "toolmaker", "sheetmetal"])
    )
    fab_keywords = ["fabrication", "welding", "welder", "fitter", "metal", "machining", "toolmaker", "mechanical", "boiler"]
    if is_fab_occ:
        is_rel = _has_keyword(f, fab_keywords)
        return is_rel, "Field matches fabrication/engineering trade discipline" if is_rel else f"Field '{field_of_study}' is not fabrication/engineering trade"

    # Fallback keyword overlap
    f_words = {w for w in re.findall(r"\b[a-zA-Z]{3,}\b", f)}
    t_words = {w for w in re.findall(r"\b[a-zA-Z]{3,}\b", title + " " + group)}
    common = f_words.intersection(t_words)
    return len(common) > 0, "Partial field overlap" if common else f"Field '{field_of_study}' has no overlap with {title}"


# ══════════════════════════════════════════════════════════════════════════
# ACS EVALUATION ENGINE
# ══════════════════════════════════════════════════════════════════════════
def evaluate_acs(
    occ: Dict[str, Any],
    profile: Dict[str, Any],
    qual_level: str,
    field_of_study: str,
    total_exp: float,
    au_exp: float,
    is_closely_related: bool = True,
    it_percentage: Optional[float] = None,
) -> Dict[str, Any]:
    """Evaluate candidate profile against Australian Computer Society (ACS) rules."""
    code = occ.get("code") or "261313"
    title = occ.get("title") or "ICT Professional"
    occ_category = occ.get("acs_category") or "General IT"
    
    # 1. Determine Qualification Classification: IT Major, IT Minor, or Non-IT
    f_lower = _normalize_str(field_of_study)
    q_lower = _normalize_str(qual_level)

    # Keywords classification
    is_direct_it_major = any(k in f_lower for k in [
        "computer", "comput", "information technology", "cse", "software", "information systems",
        "mca", "bca", "msc it", "m.sc it", "mtech cs", "m.tech cs", "data science", "cyber", "ai", "artificial intelligence", "network"
    ]) or any(k in q_lower for k in ["mca", "bca", "b.tech cse", "btech cse", "b.tech it", "btech it", "m.tech cse", "mtech cse", "computer"])
    
    is_it_minor_or_mixed = any(k in f_lower for k in [
        "ece", "electronics", "telecommunication", "electrical and electronics", "eee", "instrumentation", "mechatronics"
    ]) or any(k in q_lower for k in ["ece", "eee", "electronics"])
    
    is_non_it = any(k in f_lower for k in [
        "commerce", "b.com", "bcom", "bba", "arts", "ba", "finance", "accounting", "civil", "mechanical", "chemical", "biotech", "management", "mba", "economics"
    ]) or any(k in q_lower for k in ["b.com", "bcom", "bba", "ba ", "b.a", "mba"]) or ("non-it" in f_lower or "non ict" in f_lower or "non-ict" in f_lower)

    # Explicit threshold check if it_percentage provided
    if it_percentage is not None:
        if q_lower in ("master", "postgraduate", "mca", "msc", "mtech"):
            major_thresh = 50.0
        else:
            major_thresh = 33.0
        minor_thresh = major_thresh * (2.0 / 3.0)
        
        if it_percentage >= major_thresh:
            bucket = "IT Major"
        elif it_percentage >= minor_thresh:
            bucket = "IT Minor"
        else:
            bucket = "Non-IT / Insufficient IT"
    else:
        if is_direct_it_major:
            bucket = "IT Major"
        elif is_it_minor_or_mixed:
            bucket = "IT Minor"
        elif is_non_it:
            bucket = "Non-IT / Insufficient IT"
        else:
            # Check qualification level
            if any(k in q_lower for k in ["bachelor", "master", "doctorate"]):
                bucket = "IT Major" if ("it" in f_lower or "comput" in f_lower) else "Non-IT / Insufficient IT"
            elif "diploma" in q_lower:
                bucket = "IT Major (Diploma)" if ("it" in f_lower or "comput" in f_lower) else "Non-IT / Insufficient IT"
            else:
                bucket = "Non-IT / Insufficient IT"

    is_degree_level = any(k in q_lower for k in ["bachelor", "master", "doctorate", "phd", "postgraduate", "b.tech", "be", "mca", "bca", "m.tech", "b.sc", "m.sc"]) or (bucket in ("IT Major", "IT Minor") and not "diploma" in q_lower)
    is_diploma_level = "diploma" in q_lower or "associate" in q_lower

    # 2. Determine Required Experience & Deduction
    rpl_required = False
    pathway_name = ""
    deducted_years = 0.0
    outcome = "Likely Positive"
    reasoning_parts = []
    rpl_details = {}

    if bucket == "IT Major" and is_degree_level:
        if is_closely_related:
            pathway_name = "ACS General Skills — Bachelor/Master with IT Major (Closely Related)"
            deducted_years = 2.0
            required_exp = 2.0
            reasoning_parts.append(
                f"Your qualification ({qual_level or 'Bachelor/Master'} in {field_of_study or 'IT/CSE'}) is assessed as an AQF Bachelor degree or higher with an IT Major (at least 33% ICT content for Bachelor / 50% for Master's) "
                f"that is closely related (at least 65% ICT units) to nominated ANZSCO {code} ({title})."
            )
            reasoning_parts.append(
                "Under ACS General Skills criteria, 2 years of relevant professional ICT employment completed in the last 10 years "
                "are required to meet skills suitability. These 2 years constitute the qualifying period (Requirement Met Date) and are deducted from your total experience."
            )
        else:
            pathway_name = "ACS General Skills — Bachelor/Master with IT Major (Not Closely Related)"
            deducted_years = 4.0
            required_exp = 4.0
            reasoning_parts.append(
                f"Your qualification is assessed as an IT Major, but the ICT units are NOT closely related (under 65% match) to nominated ANZSCO {code} ({title})."
            )
            reasoning_parts.append(
                "Under ACS rules, 4 years of relevant professional ICT employment anytime are required to meet suitability, resulting in a 4.0-year qualifying deduction."
            )

    elif bucket == "IT Minor" and is_degree_level:
        if is_closely_related:
            pathway_name = "ACS General Skills — Bachelor/Master with IT Minor (Closely Related)"
            deducted_years = 5.0
            required_exp = 5.0
            reasoning_parts.append(
                f"Your qualification (e.g. ECE/EEE or mixed engineering) is assessed as an IT Minor (ICT content between 22% and 32%) closely related to {code}."
            )
            reasoning_parts.append(
                "ACS requires 5 years of relevant ICT experience in the past 10 years (or 6 years anytime) to establish suitability. 5.0 years are deducted before the Requirement Met Date."
            )
        else:
            pathway_name = "ACS General Skills — Bachelor/Master with IT Minor (Not Closely Related)"
            deducted_years = 6.0
            required_exp = 6.0
            reasoning_parts.append(
                f"Your qualification is assessed as an IT Minor and is NOT closely related to nominated ANZSCO {code}."
            )
            reasoning_parts.append(
                "ACS requires 6 years of relevant ICT work experience anytime, resulting in a 6.0-year deduction for skills suitability."
            )

    elif bucket == "IT Major" and is_diploma_level:
        if is_closely_related:
            pathway_name = "ACS General Skills — Diploma / Advanced Diploma with IT Major (Closely Related)"
            deducted_years = 5.0
            required_exp = 5.0
            reasoning_parts.append(
                "Your qualification is assessed as an AQF Diploma/Advanced Diploma with at least 1 full academic year of closely related ICT content."
            )
            reasoning_parts.append(
                "Under ACS rules, 5 years of relevant ICT experience in the last 10 years (or 6 years anytime) are required and deducted before the Requirement Met Date."
            )
        else:
            pathway_name = "ACS General Skills — Diploma with IT Major (Not Closely Related)"
            deducted_years = 6.0
            required_exp = 6.0
            reasoning_parts.append(
                "Your Diploma has IT Major content but is not closely related to the nominated occupation. 6 years of experience are required and deducted."
            )

    else:
        # Non-IT / Insufficient IT -> RPL Pathway
        bucket = "Non-IT / Insufficient IT"
        rpl_required = True
        pathway_name = "ACS Recognition of Prior Learning (RPL) Pathway"
        deducted_years = 6.0
        required_exp = 6.0
        rpl_details = {
            "required": True,
            "reports_needed": 2,
            "report_timeline": "1 project from the last 2 years + 1 project from the last 4 years",
            "acs_rpl_review_fee_aud": 625,
            "total_rpl_application_fee_aud": 1498,
        }
        reasoning_parts.append(
            f"Your qualification ({qual_level or 'Tertiary Award'} in {field_of_study or 'Non-IT field'}) is classified as Non-ICT / Insufficient IT content under ACS InfoHub guidelines."
        )
        reasoning_parts.append(
            "Under the ACS RPL (Recognition of Prior Learning) pathway, applicants without a tertiary ICT degree must demonstrate at least 6 years of relevant full-time professional ICT experience (at least 20 hours/week) to achieve a positive skills assessment outcome."
        )
        reasoning_parts.append(
            "All 6 years of qualifying work experience are consumed by ACS to satisfy skills suitability (the Requirement Met Date). "
            "Under Department of Home Affairs (DHA) migration rules, only employment completed AFTER the Requirement Met Date can be claimed for points in the General Skilled Migration (GSM) points test. "
            f"Consequently, with {total_exp:.1f} years of experience, exactly {deducted_years:.1f} years will be deducted, leaving {max(0.0, total_exp - deducted_years):.1f} years eligible for migration points."
        )

    # 3. Assessment Outcome Evaluation
    if total_exp < required_exp:
        shortfall = required_exp - total_exp
        outcome = "Ineligible / Experience Shortfall"
        reasoning_parts.append(
            f"⚠️ Experience Shortfall: You currently have {total_exp:.1f} years of relevant experience, but this ACS pathway requires a minimum of {required_exp:.1f} years. "
            f"You need an additional {shortfall:.1f} year{'s' if shortfall != 1.0 else ''} of paid professional ICT employment (20+ hrs/wk) to be eligible for positive assessment."
        )
    else:
        if rpl_required:
            outcome = "Positive via RPL Pathway"
        else:
            outcome = "Likely Positive Assessment"

    # 4. Points calculation after deduction
    points_claimable_years = max(0.0, total_exp - deducted_years)
    overseas_pts, overseas_desc = calculate_gsm_experience_points(points_claimable_years, in_australia=False)
    
    # 5. Documents & Risk Checklist
    required_docs = [
        "Passport bio-data page (colour copy)",
        "Secondary Government ID (Aadhaar / PAN / Driver Licence)",
        "All Degree Certificates and Consolidated + Semester-wise Marksheets",
        "Official Academic Transcripts (with subject syllabus for ICT mapping)",
        "Employer Reference Letters on official letterhead detailing roles, responsibilities, tools & weekly hours (20+ hrs/wk)",
        "Two forms of payment evidence covering start and end dates (Form 16/ITR, EPFO/PF records, Bank Salary Credits, Payslips)",
        "Current Comprehensive Résumé / CV",
    ]
    if rpl_required:
        required_docs.insert(4, "Two ACS RPL Project Reports (1 from last 2 years, 1 from last 4 years)")

    risk_warnings = [
        "Generic HR letters omitting specific ICT duties or hours will cause assessment delays or refusal.",
        "Copied or verbatim ANZSCO duty descriptions are strictly rejected by ACS.",
        "Unpaid internships, freelance work without tax records/invoices, and periods under 20 hours/week cannot be counted.",
        "Ensure Form 16 / ITR or bank statements clearly display the employer name and salary credits.",
    ]

    return {
        "authority_code": "ACS",
        "authority_name": "Australian Computer Society",
        "occupation_code": code,
        "occupation_title": title,
        "qualification_bucket": bucket,
        "pathway_name": pathway_name,
        "assessment_outcome": outcome,
        "is_positive": outcome in ("Likely Positive Assessment", "Positive via RPL Pathway"),
        "rpl_required": rpl_required,
        "rpl_details": rpl_details,
        "total_experience_years": total_exp,
        "deducted_years": deducted_years,
        "points_claimable_years": points_claimable_years,
        "points_claimable_points": overseas_pts,
        "points_description": overseas_desc,
        "deemed_skilled_summary": (
            f"{deducted_years:.1f} years deducted for skills suitability · {points_claimable_years:.1f} years points-claimable ({overseas_pts} pts)"
        ),
        "justification": "\n\n".join(reasoning_parts),
        "required_documents": required_docs,
        "risk_warnings": risk_warnings,
        "screening_checklist_notes": "Verify subject syllabus, ensure 65% duty alignment, collect Form 16/EPFO records.",
    }


# ══════════════════════════════════════════════════════════════════════════
# VETASSESS PROFESSIONAL EVALUATION ENGINE
# ══════════════════════════════════════════════════════════════════════════
def evaluate_vetassess_professional(
    occ: Dict[str, Any],
    profile: Dict[str, Any],
    qual_level: str,
    field_of_study: str,
    total_exp: float,
    au_exp: float,
    is_highly_relevant_major: Optional[bool] = None,
    has_additional_relevant_qual: bool = False,
    exp_in_last_5_years: Optional[float] = None,
) -> Dict[str, Any]:
    """Evaluate candidate profile against VETASSESS Professional Groups (A, B, C, D, E, F)."""
    code = occ.get("code") or "224711"
    title = occ.get("title") or "Management Consultant"
    group = (occ.get("vetassess_group") or occ.get("group") or "B").upper()
    if group not in ("A", "B", "C", "D", "E", "F"):
        group = "B"

    q_lower = _normalize_str(qual_level)
    f_lower = _normalize_str(field_of_study)
    
    if is_highly_relevant_major is None:
        is_highly_relevant_major, _ = is_field_relevant_to_occupation(field_of_study, occ)

    if exp_in_last_5_years is None:
        exp_in_last_5_years = min(total_exp, 5.0)

    deducted_years = 0.0
    required_exp = 1.0
    pathway_name = ""
    outcome = "Likely Positive"
    reasoning_parts = []
    pre_qual_applied = False

    is_bachelor_or_higher = any(k in q_lower for k in ["bachelor", "master", "doctorate", "phd", "postgraduate", "b.tech", "be", "b.com", "bba", "ba", "b.sc", "m.sc", "mba"]) or any(k in f_lower for k in ["bachelor", "master", "degree"])
    is_diploma = any(k in q_lower for k in ["diploma", "associate degree", "advanced diploma"])
    is_cert_iv = any(k in q_lower for k in ["certificate iv", "cert iv", "cert 4", "certificate 4"])
    is_cert_iii = any(k in q_lower for k in ["certificate iii", "cert iii", "cert 3", "certificate 3"])

    # ── Group A: Skill Level 1 (Bachelor+ in highly relevant field only) ──
    if group == "A":
        pathway_name = "VETASSESS Group A — AQF Bachelor+ in Highly Relevant Field"
        required_exp = 1.0
        deducted_years = 1.0
        
        if not is_bachelor_or_higher and qual_level:
            outcome = "Ineligible / Qualification Level Below Requirement"
            reasoning_parts.append(
                f"ANZSCO {code} ({title}) is a VETASSESS Group A occupation requiring an AQF Bachelor degree or higher. "
                f"Your qualification ({qual_level}) does not meet the minimum AQF level."
            )
        elif not is_highly_relevant_major:
            outcome = "Ineligible / Field of Study Not Highly Relevant"
            reasoning_parts.append(
                f"Group A occupations strictly require an AQF Bachelor degree or higher in a HIGHLY RELEVANT field of study. "
                "Pre-qualification experience and non-relevant degree compensations do NOT apply to Group A occupations."
            )
        else:
            reasoning_parts.append(
                f"Your qualification is assessed as an AQF Bachelor degree or higher in a highly relevant field for ANZSCO {code} ({title})."
            )
            reasoning_parts.append(
                "Group A criteria require at least 1 year of post-qualification highly relevant paid employment (20+ hours/week) in the last 5 years. "
                "This 1 year serves as the qualifying period (Date Deemed Skilled) and is deducted from points-claimable experience."
            )

    # ── Group B: Skill Level 1 (Bachelor+ with multiple pathways) ──
    elif group == "B":
        if not is_bachelor_or_higher and qual_level:
            outcome = "Ineligible / Qualification Level Below Requirement"
            reasoning_parts.append(
                f"ANZSCO {code} ({title}) is a VETASSESS Group B occupation requiring at least an AQF Bachelor degree."
            )
        elif is_highly_relevant_major:
            pathway_name = "VETASSESS Group B — Pathway 1 (Highly Relevant Major)"
            required_exp = 1.0
            deducted_years = 1.0
            reasoning_parts.append(
                f"Your AQF Bachelor degree or higher is in a highly relevant field for ANZSCO {code} ({title})."
            )
            reasoning_parts.append(
                "Under Pathway 1, at least 1 year of post-qualification highly relevant employment (20+ hrs/wk) within the last 5 years is required and deducted."
            )
        elif has_additional_relevant_qual:
            pathway_name = "VETASSESS Group B — Pathway 2 (Non-relevant Bachelor + Relevant AQF Diploma)"
            required_exp = 2.0
            deducted_years = 2.0
            reasoning_parts.append(
                "You hold an AQF Bachelor degree with a non-relevant major, plus an additional highly relevant AQF Diploma."
            )
            reasoning_parts.append(
                "Under Pathway 2, 2 years of post-qualification highly relevant employment in the last 5 years are required and deducted."
            )
        elif total_exp >= 6.0 and exp_in_last_5_years >= 1.0:
            pathway_name = "VETASSESS Group B — Pathway 4 (Pre-qualification Experience)"
            required_exp = 6.0
            deducted_years = 5.0
            pre_qual_applied = True
            reasoning_parts.append(
                "Your degree major is not highly relevant, but you meet the Group B Pre-qualification criteria: at least 5 years of relevant employment pre-qualification "
                "plus at least 1 year of highly relevant employment at the required skill level in the last 5 years."
            )
            reasoning_parts.append(
                "The 5-year qualifying period is deducted before your Date Deemed Skilled."
            )
        else:
            pathway_name = "VETASSESS Group B — Pathway 3 (Non-relevant Major, Post-qualification)"
            required_exp = 3.0
            deducted_years = 3.0
            reasoning_parts.append(
                f"Your AQF Bachelor degree is in a field that is not highly relevant to ANZSCO {code}."
            )
            reasoning_parts.append(
                "Under Pathway 3, 3 years of post-qualification highly relevant paid employment (20+ hrs/wk) in the last 5 years are required and deducted."
            )

    # ── Group C: Skill Level 2 (AQF Diploma+) ──
    elif group == "C":
        if not (is_bachelor_or_higher or is_diploma) and qual_level:
            outcome = "Ineligible / Qualification Level Below Requirement"
            reasoning_parts.append(
                f"ANZSCO {code} ({title}) is a VETASSESS Group C occupation requiring at least an AQF Diploma."
            )
        elif is_highly_relevant_major:
            pathway_name = "VETASSESS Group C — Pathway 1 (Highly Relevant Diploma)"
            required_exp = 1.0
            deducted_years = 1.0
            reasoning_parts.append(
                f"You hold an AQF Diploma or higher in a highly relevant field for ANZSCO {code} ({title})."
            )
            reasoning_parts.append(
                "Requires at least 1 year of post-qualification highly relevant employment in the last 5 years (1.0 year deducted)."
            )
        elif total_exp >= 4.0 and exp_in_last_5_years >= 1.0:
            pathway_name = "VETASSESS Group C — Pathway 4 (Pre-qualification Experience)"
            required_exp = 4.0
            deducted_years = 3.0
            pre_qual_applied = True
            reasoning_parts.append(
                "Group C Pre-qualification pathway applied: 3 years of relevant employment pre-qualification + 1 year highly relevant in the last 5 years."
            )
            reasoning_parts.append(
                "3.0 years qualifying period deducted before Date Deemed Skilled."
            )
        else:
            pathway_name = "VETASSESS Group C — Pathway 3 (Non-relevant Diploma)"
            required_exp = 2.0
            deducted_years = 2.0
            reasoning_parts.append(
                "You hold an AQF Diploma or higher with a non-relevant major. Requires 2 years of post-qualification highly relevant employment in the last 5 years (2.0 years deducted)."
            )

    # ── Group D: Skill Level 3 (AQF Cert III / IV) ──
    elif group == "D":
        if is_cert_iv or is_diploma or is_bachelor_or_higher:
            if is_highly_relevant_major:
                pathway_name = "VETASSESS Group D — Pathway 1 (Cert IV Highly Relevant)"
                required_exp = 1.0
                deducted_years = 1.0
            else:
                pathway_name = "VETASSESS Group D — Pathway 2 (Cert IV Non-relevant Major)"
                required_exp = 2.0
                deducted_years = 2.0
        elif is_cert_iii:
            pathway_name = "VETASSESS Group D — Pathway 3 (Cert III Highly Relevant)"
            required_exp = 3.0
            deducted_years = 3.0
        elif total_exp >= 4.0 and exp_in_last_5_years >= 1.0:
            pathway_name = "VETASSESS Group D — Pathway 4 (Pre-qualification Experience)"
            required_exp = 4.0
            deducted_years = 3.0
            pre_qual_applied = True
        else:
            pathway_name = "VETASSESS Group D — Standard Pathway"
            required_exp = 2.0
            deducted_years = 2.0
        reasoning_parts.append(
            f"VETASSESS Group D occupation ({code} · {title}): evaluated under AQF Certificate III/IV criteria."
        )

    # ── Group E: Skill Level 2 (Advanced Diploma / Associate Degree in highly relevant field) ──
    elif group == "E":
        pathway_name = "VETASSESS Group E — Advanced Diploma in Highly Relevant Field"
        required_exp = 1.0
        deducted_years = 1.0
        reasoning_parts.append(
            f"Group E requires an AQF Advanced Diploma/Associate Degree in a highly relevant field + 1 year post-qualification experience in the last 5 years."
        )

    # ── Group F: Skill Level 3/4 (Cert II/III Sports & Recreation) ──
    else:
        pathway_name = "VETASSESS Group F — Sports & Recreation Occupations"
        required_exp = 1.0 if is_highly_relevant_major else 2.0
        deducted_years = required_exp
        reasoning_parts.append(
            f"Group F evaluated under AQF Certificate II/III criteria (requires {required_exp:.0f} yr(s) qualifying employment)."
        )

    # Check experience shortfall
    if total_exp < required_exp:
        shortfall = required_exp - total_exp
        outcome = "Ineligible / Experience Shortfall"
        reasoning_parts.append(
            f"⚠️ Experience Shortfall: You have {total_exp:.1f} years of relevant experience, but this {group} pathway requires {required_exp:.1f} years. "
            f"An additional {shortfall:.1f} year{'s' if shortfall != 1.0 else ''} of paid employment (20+ hrs/wk) is required."
        )
    elif exp_in_last_5_years < 1.0 and group in ("A", "B", "C", "D", "E"):
        outcome = "Borderline / Recency Requirement Not Met"
        reasoning_parts.append(
            "⚠️ Recency Warning: VETASSESS requires at least 1 year of highly relevant paid employment within the last 5 years. "
            "Please ensure employment currency before lodgement."
        )

    points_claimable_years = max(0.0, total_exp - deducted_years)
    overseas_pts, overseas_desc = calculate_gsm_experience_points(points_claimable_years, in_australia=False)

    required_docs = [
        "Colour photograph + 3 forms of ID (Passport bio-page + Government photo ID)",
        "Degree / Diploma / Certificate Testamur and full transcripts / marksheets",
        "Formal Statement of Service on employer letterhead (roles, exact dates, weekly hours 20+, salary, referee details)",
        "Payment Evidence covering claimed periods (Form 16/ITR, EPFO/PF records, bank salary credits, payslips)",
        "Detailed Résumé / CV formatted to VETASSESS standards",
    ]
    if group in ("A", "B") and any(k in title.lower() for k in ["manager", "consultant", "administrator", "director"]):
        required_docs.append("Organisational Chart on company letterhead showing your position, direct reports, and reporting line")

    risk_warnings = [
        "VETASSESS strictly enforces the 20 hours/week paid employment rule; unpaid leave or volunteer work is excluded.",
        "Tasks must match the ANZSCO description at the required skill level (not junior/entry level).",
        "Pre-qualification experience cannot be claimed for Group A or Group E occupations.",
        "For Indian applicants: Form 16 / tax assessment and bank statements showing employer salary credits are mandatory.",
    ]

    return {
        "authority_code": "VETASSESS",
        "authority_name": "Vocational Education and Training Assessment Services",
        "occupation_code": code,
        "occupation_title": title,
        "vetassess_group": group,
        "pathway_name": pathway_name,
        "assessment_outcome": outcome,
        "is_positive": outcome in ("Likely Positive Assessment", "Positive via RPL Pathway", "Likely Positive"),
        "rpl_required": False,
        "rpl_details": {},
        "total_experience_years": total_exp,
        "deducted_years": deducted_years,
        "points_claimable_years": points_claimable_years,
        "points_claimable_points": overseas_pts,
        "points_description": overseas_desc,
        "deemed_skilled_summary": (
            f"VETASSESS Group {group} · {deducted_years:.1f} yr(s) qualifying deduction · {points_claimable_years:.1f} yr(s) points-claimable ({overseas_pts} pts)"
        ),
        "justification": "\n\n".join(reasoning_parts),
        "required_documents": required_docs,
        "risk_warnings": risk_warnings,
        "screening_checklist_notes": f"Verify Group {group} criteria, check AQF comparability of qualification, ensure 20+ hrs/wk payment proof.",
    }


# ══════════════════════════════════════════════════════════════════════════
# TRA & VETASSESS TRADE EVALUATION ENGINE
# ══════════════════════════════════════════════════════════════════════════
def evaluate_tra_and_trade(
    occ: Dict[str, Any],
    profile: Dict[str, Any],
    qual_level: str,
    field_of_study: str,
    total_exp: float,
    au_exp: float,
    is_licensed_trade: bool = False,
    has_formal_trade_training: bool = False,
    exp_in_last_3_years: Optional[float] = None,
) -> Dict[str, Any]:
    """Evaluate candidate profile against Trades Recognition Australia (TRA) / VETASSESS Trade RTO rules."""
    code = occ.get("code") or "321211"
    title = occ.get("title") or "Motor Mechanic (General)"
    is_rto_vetassess = occ.get("vetassess_approved_rto") or occ.get("is_vetassess_trade") or False

    if exp_in_last_3_years is None:
        exp_in_last_3_years = min(total_exp, 3.0)

    # Determine required experience based on licensing & formal training
    if is_licensed_trade:
        if has_formal_trade_training:
            pathway_name = "TRA / Trade OSAP — Licensed Trade with Relevant Formal Training"
            required_exp = 4.0
            deducted_years = 4.0
        else:
            pathway_name = "TRA / Trade OSAP — Licensed Trade without Formal Training"
            required_exp = 6.0
            deducted_years = 6.0
    else:
        if has_formal_trade_training:
            pathway_name = "TRA / Trade OSAP — Non-Licensed Trade with Relevant Formal Training"
            required_exp = 3.0
            deducted_years = 3.0
        else:
            pathway_name = "TRA / Trade OSAP — Non-Licensed Trade without Formal Training"
            required_exp = 5.0
            deducted_years = 5.0

    outcome = "Likely Positive"
    reasoning_parts = []
    
    auth_label = "TRA (Trades Recognition Australia)"
    if is_rto_vetassess:
        auth_label = "TRA (via VETASSESS as approved RTO under OSAP/TSS)"

    reasoning_parts.append(
        f"ANZSCO {code} ({title}) is assessed by {auth_label} under Trade Skills Assessment rules."
    )
    reasoning_parts.append(
        f"Pathway: {pathway_name}. Minimum experience requirement is {required_exp:.0f} years of full-time (or pro-rata part-time) paid trade work experience."
    )

    if total_exp < required_exp:
        shortfall = required_exp - total_exp
        outcome = "Ineligible / Experience Shortfall"
        reasoning_parts.append(
            f"⚠️ Experience Shortfall: You have {total_exp:.1f} years of trade experience, but this pathway requires {required_exp:.1f} years. "
            f"Shortfall is {shortfall:.1f} year{'s' if shortfall != 1.0 else ''}."
        )
    elif exp_in_last_3_years < 1.0:
        outcome = "Borderline / Currency Requirement Not Met"
        reasoning_parts.append(
            "⚠️ Currency Rule: TRA / VETASSESS Trade requires at least 12 months (1.0 year) of employment in the nominated trade occupation within the last 3 years."
        )
    else:
        reasoning_parts.append(
            f"You meet the {required_exp:.0f}-year experience requirement and recent currency rule (12+ months in last 3 years). "
            f"{deducted_years:.1f} years are deducted as the qualifying benchmark before points-claimable skilled employment."
        )

    points_claimable_years = max(0.0, total_exp - deducted_years)
    overseas_pts, overseas_desc = calculate_gsm_experience_points(points_claimable_years, in_australia=False)

    required_docs = [
        "Passport bio-data page (colour copy)",
        "Apprenticeship / Trade Qualification certificate & transcript (if held)",
        "Detailed Employer Statements of Service specifying exact trade tasks, machinery/tools used, and hours",
        "Payment Evidence for every claimed year (payslips, tax records/Form 16, bank statements)",
        "Workplace logbook / Job sheets / Photographs / Tool lists where available",
        "Comprehensive trade CV / Résumé",
    ]

    risk_warnings = [
        "TRA requires substantial documentary proof of hands-on trade work; job descriptions must be specific to tools and daily trade duties.",
        "Cash-in-hand or unverifiable informal work cannot be accepted for trade assessment.",
        "Must demonstrate at least 12 months employment in the nominated trade within the last 3 years.",
    ]

    return {
        "authority_code": "TRA",
        "authority_name": "Trades Recognition Australia (TRA)",
        "occupation_code": code,
        "occupation_title": title,
        "vetassess_group": None,
        "is_trade": True,
        "vetassess_approved_rto": is_rto_vetassess,
        "pathway_name": pathway_name,
        "assessment_outcome": outcome,
        "is_positive": outcome in ("Likely Positive Assessment", "Positive via RPL Pathway", "Likely Positive"),
        "rpl_required": False,
        "rpl_details": {},
        "total_experience_years": total_exp,
        "deducted_years": deducted_years,
        "points_claimable_years": points_claimable_years,
        "points_claimable_points": overseas_pts,
        "points_description": overseas_desc,
        "deemed_skilled_summary": (
            f"TRA Trade OSAP · {deducted_years:.1f} yr(s) qualifying deduction · {points_claimable_years:.1f} yr(s) points-claimable ({overseas_pts} pts)"
        ),
        "justification": "\n\n".join(reasoning_parts),
        "required_documents": required_docs,
        "risk_warnings": risk_warnings,
        "screening_checklist_notes": "Verify trade apprenticeship / certificate III/IV comparability, practical workplace evidence, and payment records for all claimed years.",
    }


# ══════════════════════════════════════════════════════════════════════════
# ANMAC EVALUATION ENGINE (Nursing & Midwifery)
# ══════════════════════════════════════════════════════════════════════════
def evaluate_anmac(
    occ: Dict[str, Any],
    profile: Dict[str, Any],
    qual_level: str,
    field_of_study: str,
    total_exp: float,
    au_exp: float,
) -> Dict[str, Any]:
    code = occ.get("code") or "254499"
    title = occ.get("title") or "Registered Nurse"
    q_lower = _normalize_str(qual_level)
    f_lower = _normalize_str(field_of_study)

    has_nursing_qual = any(k in f_lower for k in ["nurs", "health", "midwif", "clinical", "medical"]) or any(k in q_lower for k in ["b.sc nurs", "bsc nurs", "nursing", "m.sc nurs", "msc nurs", "gnm", "bachelor of nursing"])
    has_degree = any(k in q_lower for k in ["bachelor", "master", "doctorate", "degree", "b.sc", "bsc", "m.sc", "msc"]) or not q_lower

    if has_nursing_qual and has_degree:
        outcome = "Likely Positive Assessment"
        is_pos = True
        deducted_years = 0.0  # ANMAC does not deduct years for point test; graduation date is deemed skilled date
        reasoning = (
            f"You hold a tertiary nursing qualification ({qual_level or 'Bachelor'} in {field_of_study or 'Nursing'}). "
            f"ANMAC assesses registered nurse qualifications at AQF Bachelor degree level or higher. "
            f"0.0 years deducted: all post-registration nursing employment ({total_exp:.1f} years) is deemed skilled and claimable for GSM points."
        )
    elif has_nursing_qual:
        outcome = "Likely Positive Assessment (Diploma / Enrolled Nurse Pathway)"
        is_pos = True
        deducted_years = 0.0
        reasoning = (
            f"You hold a nursing diploma/qualification ({qual_level or 'Diploma'} in {field_of_study or 'Nursing'}). "
            f"ANMAC assesses enrolled nurse / overseas nursing qualifications. Post-registration experience ({total_exp:.1f} years) is claimable."
        )
    else:
        outcome = "Review Required (Nursing Degree Verification Needed)"
        is_pos = False
        deducted_years = 0.0
        reasoning = (
            f"ANMAC requires an accredited Bachelor or Master degree in Nursing or Midwifery. "
            f"Your recorded education ({qual_level} in {field_of_study}) must be verified against ANMAC accredited program standards."
        )

    points_claimable_years = total_exp
    overseas_pts, overseas_desc = calculate_gsm_experience_points(points_claimable_years, in_australia=False)

    return {
        "authority_code": "ANMAC",
        "authority_name": "Australian Nursing and Midwifery Accreditation Council (ANMAC)",
        "occupation_code": code,
        "occupation_title": title,
        "pathway_name": "ANMAC Full Skills Assessment (International Registered Nurse)",
        "assessment_outcome": outcome,
        "is_positive": is_pos,
        "rpl_required": False,
        "rpl_details": {},
        "total_experience_years": total_exp,
        "deducted_years": deducted_years,
        "points_claimable_years": points_claimable_years,
        "points_claimable_points": overseas_pts,
        "points_description": overseas_desc,
        "deemed_skilled_summary": f"ANMAC Nursing · 0.0 yrs deducted · {points_claimable_years:.1f} yrs points-claimable ({overseas_pts} pts)",
        "justification": reasoning,
        "required_documents": [
            "Passport bio-data page (colour copy)",
            "Degree / Diploma Certificate in Nursing or Midwifery",
            "Official Academic Transcripts with clinical placement hour breakdown (minimum 800 hours)",
            "Current Nursing Registration Certificate from Home Country / State Nursing Council (e.g. State Nursing Council / INC / NMCN)",
            "Verification of Registration / Certificate of Good Standing (sent directly to ANMAC)",
            "Detailed Professional Reference Letters on Hospital Letterhead specifying ward/specialty, duties, and weekly hours (20+ hrs/wk)",
            "Payment Evidence (payslips, Form 16 / tax assessments, bank statements showing salary credits)",
            "English Language Test Report (IELTS 7.0 each / PTE 65 each / OET B each)",
        ],
        "risk_warnings": [
            "Must achieve minimum English score (IELTS 7.0 in each band / PTE 65 in each band / OET B in each sub-test).",
            "Nursing registration with home nursing council must be active and in good standing.",
            "Clinical practice hours during degree must meet Australian nursing educational equivalents.",
        ],
        "screening_checklist_notes": "Verify nursing council registration, English test scores (IELTS 7.0/PTE 65), and clinical placement transcript.",
    }


# ══════════════════════════════════════════════════════════════════════════
# ACCOUNTING & FINANCE EVALUATION ENGINE (CPA / CA ANZ / IPA)
# ══════════════════════════════════════════════════════════════════════════
def evaluate_accounting(
    occ: Dict[str, Any],
    profile: Dict[str, Any],
    qual_level: str,
    field_of_study: str,
    total_exp: float,
    au_exp: float,
) -> Dict[str, Any]:
    code = occ.get("code") or "221111"
    title = occ.get("title") or "Accountant (General)"
    q_lower = _normalize_str(qual_level)
    f_lower = _normalize_str(field_of_study)

    has_acc_qual = any(k in f_lower for k in ["account", "finance", "commerce", "b.com", "bcom", "m.com", "mcom", "ca", "cpa", "cfa", "mba finance"]) or any(k in q_lower for k in ["b.com", "bcom", "m.com", "ca", "cpa", "accounting"])
    has_degree = any(k in q_lower for k in ["bachelor", "master", "doctorate", "degree", "b.com", "m.com", "ca"]) or not q_lower

    if has_acc_qual and has_degree:
        outcome = "Likely Positive Assessment"
        is_pos = True
        deducted_years = 0.0
        reasoning = (
            f"You hold an Accounting/Commerce qualification ({qual_level or 'Bachelor'} in {field_of_study or 'Accounting'}). "
            f"CPA Australia / CA ANZ / IPA assess accounting degrees for core mandatory syllabus areas. "
            f"All post-qualification professional accounting experience ({total_exp:.1f} years) is claimable for migration points."
        )
    else:
        outcome = "Review Required (Core Accounting Subjects Assessment)"
        is_pos = False
        deducted_years = 0.0
        reasoning = (
            f"Assessing bodies (CPA / CA ANZ / IPA) require an AQF Bachelor degree covering 7-8 mandatory core knowledge areas "
            f"(Financial Accounting, Management Accounting, Taxation Law, Commercial Law, Audit, Economics, Quantitative Methods)."
        )

    points_claimable_years = total_exp
    overseas_pts, overseas_desc = calculate_gsm_experience_points(points_claimable_years, in_australia=False)

    return {
        "authority_code": "CPA Australia",
        "authority_name": "CPA Australia / CA ANZ / IPA",
        "occupation_code": code,
        "occupation_title": title,
        "pathway_name": "CPA / CA ANZ / IPA Full Skills Assessment",
        "assessment_outcome": outcome,
        "is_positive": is_pos,
        "rpl_required": False,
        "rpl_details": {},
        "total_experience_years": total_exp,
        "deducted_years": deducted_years,
        "points_claimable_years": points_claimable_years,
        "points_claimable_points": overseas_pts,
        "points_description": overseas_desc,
        "deemed_skilled_summary": f"CPA/CAANZ Accounting · 0.0 yrs deducted · {points_claimable_years:.1f} yrs points-claimable ({overseas_pts} pts)",
        "justification": reasoning,
        "required_documents": [
            "Passport bio-data page",
            "Degree Certificate & Official Transcripts covering all academic years",
            "Detailed Course Syllabi / Subject Descriptions for accounting subjects studied",
            "Employment Reference Letters detailing accounting duties on company letterhead",
            "Proof of Paid Employment (payslips, Form 16, tax summaries, bank statements)",
            "English Language Test Report (IELTS 7.0 each / PTE 65 each / Accounting Professional Year)",
        ],
        "risk_warnings": [
            "Must cover 7 to 8 core knowledge areas; missing subjects may require non-award bridging units.",
            "English proficiency threshold is mandatory for positive assessment (IELTS 7.0 each / PTE 65 each).",
        ],
        "screening_checklist_notes": "Verify syllabus coverage for Australian tax/law and accounting core subjects.",
    }


# ══════════════════════════════════════════════════════════════════════════
# TEACHING EVALUATION ENGINE (AITSL)
# ══════════════════════════════════════════════════════════════════════════
def evaluate_aitsl(
    occ: Dict[str, Any],
    profile: Dict[str, Any],
    qual_level: str,
    field_of_study: str,
    total_exp: float,
    au_exp: float,
) -> Dict[str, Any]:
    code = occ.get("code") or "241213"
    title = occ.get("title") or "Teacher"
    q_lower = _normalize_str(qual_level)
    f_lower = _normalize_str(field_of_study)

    has_teach_qual = any(k in f_lower for k in ["teach", "educat", "b.ed", "bed", "m.ed", "med", "pgce", "early childhood", "primary", "secondary"]) or any(k in q_lower for k in ["b.ed", "bed", "m.ed", "med", "teaching", "education"])

    if has_teach_qual:
        outcome = "Likely Positive Assessment"
        is_pos = True
        deducted_years = 0.0
        reasoning = (
            f"You hold a teaching/education qualification ({qual_level or 'Bachelor'} in {field_of_study or 'Education'}). "
            f"AITSL requires a minimum of 4 years higher education study including 1 year of Initial Teacher Education (ITE) "
            f"and 45 days of supervised teaching practice. Post-qualification experience ({total_exp:.1f} years) is claimable."
        )
    else:
        outcome = "Review Required (Initial Teacher Education Assessment)"
        is_pos = False
        deducted_years = 0.0
        reasoning = (
            f"AITSL mandates at least 4 years full-time higher education study including a recognized Initial Teacher Education (ITE) "
            f"degree with at least 45 days of assessed supervised school teaching practice."
        )

    points_claimable_years = total_exp
    overseas_pts, overseas_desc = calculate_gsm_experience_points(points_claimable_years, in_australia=False)

    return {
        "authority_code": "AITSL",
        "authority_name": "Australian Institute for Teaching and School Leadership (AITSL)",
        "occupation_code": code,
        "occupation_title": title,
        "pathway_name": "AITSL Teacher Skills Assessment",
        "assessment_outcome": outcome,
        "is_positive": is_pos,
        "rpl_required": False,
        "rpl_details": {},
        "total_experience_years": total_exp,
        "deducted_years": deducted_years,
        "points_claimable_years": points_claimable_years,
        "points_claimable_points": overseas_pts,
        "points_description": overseas_desc,
        "deemed_skilled_summary": f"AITSL Teaching · 0.0 yrs deducted · {points_claimable_years:.1f} yrs points-claimable ({overseas_pts} pts)",
        "justification": reasoning,
        "required_documents": [
            "Passport bio-data page",
            "Degree Certificates & Transcripts for all 4 years of tertiary study",
            "Official Supervised Teaching Practice statement confirming at least 45 days practice",
            "Current Teacher Registration / License (if applicable)",
            "Statements of Service from School Principals confirming full-time teaching experience",
            "English Language Test (Academic IELTS: 7.0 Reading, 7.0 Writing, 8.0 Speaking, 8.0 Listening)",
        ],
        "risk_warnings": [
            "AITSL strictly enforces the 45-day supervised practice rule with university verification.",
            "High English proficiency required: IELTS Reading/Writing 7.0, Speaking/Listening 8.0.",
        ],
        "screening_checklist_notes": "Verify university letter confirming 45 days supervised student teaching practice.",
    }


# ══════════════════════════════════════════════════════════════════════════
# MEDICAL PRACTITIONERS EVALUATION ENGINE (MedBA / AMC)
# ══════════════════════════════════════════════════════════════════════════
def evaluate_medba(
    occ: Dict[str, Any],
    profile: Dict[str, Any],
    qual_level: str,
    field_of_study: str,
    total_exp: float,
    au_exp: float,
) -> Dict[str, Any]:
    code = occ.get("code") or "253111"
    title = occ.get("title") or "General Practitioner"
    pts_years = total_exp
    overseas_pts, overseas_desc = calculate_gsm_experience_points(pts_years, in_australia=False)

    return {
        "authority_code": "MedBA",
        "authority_name": "Medical Board of Australia / AMC",
        "occupation_code": code,
        "occupation_title": title,
        "pathway_name": "Medical Board of Australia / AMC Assessment (Standard or Competent Authority Pathway)",
        "assessment_outcome": "Likely Positive Assessment",
        "is_positive": True,
        "rpl_required": False,
        "rpl_details": {},
        "total_experience_years": total_exp,
        "deducted_years": 0.0,
        "points_claimable_years": pts_years,
        "points_claimable_points": overseas_pts,
        "points_description": overseas_desc,
        "deemed_skilled_summary": f"MedBA/AMC · 0.0 yrs deducted · {pts_years:.1f} yrs points-claimable ({overseas_pts} pts)",
        "justification": (
            f"Assessed by Medical Board of Australia / Australian Medical Council (AMC) for ANZSCO {code} ({title}). "
            f"Requires primary medical qualification (MBBS/MD) verified through EPIC (ECFMG) plus AMC examination or Competent Authority registration."
        ),
        "required_documents": [
            "Passport bio-data page",
            "Primary Medical Degree (MBBS/MD) & Internship Completion Certificate",
            "EPIC (ECFMG) Primary-Source Verification Report",
            "Medical Council Registration / License to Practice",
            "Certificate of Good Standing from Medical Council",
            "AMC MCQ Exam Result or AMC Certificate / Specialist College Assessment",
            "English Language Test (IELTS 7.0 each / PTE 65 each / OET B each)",
        ],
        "risk_warnings": [
            "Medical degree must be from a WHO / WDOMS recognized medical school.",
            "Must complete primary-source verification via EPIC prior to AMC submission.",
        ],
        "screening_checklist_notes": "Verify WDOMS medical school listing and EPIC verification status.",
    }


# ══════════════════════════════════════════════════════════════════════════
# COMMUNITY & SOCIAL WORK (ACWA / AASW)
# ══════════════════════════════════════════════════════════════════════════
def evaluate_acwa_aasw(
    occ: Dict[str, Any],
    profile: Dict[str, Any],
    qual_level: str,
    field_of_study: str,
    total_exp: float,
    au_exp: float,
    is_aasw: bool = False,
) -> Dict[str, Any]:
    code = occ.get("code") or "272511"
    title = occ.get("title") or ("Social Worker" if is_aasw else "Community Worker")
    auth_code = "AASW" if is_aasw else "ACWA"
    auth_name = "Australian Association of Social Workers (AASW)" if is_aasw else "Australian Community Workers Association (ACWA)"
    pts_years = total_exp
    overseas_pts, overseas_desc = calculate_gsm_experience_points(pts_years, in_australia=False)

    return {
        "authority_code": auth_code,
        "authority_name": auth_name,
        "occupation_code": code,
        "occupation_title": title,
        "pathway_name": f"{auth_code} Skills Assessment",
        "assessment_outcome": "Likely Positive Assessment",
        "is_positive": True,
        "rpl_required": False,
        "rpl_details": {},
        "total_experience_years": total_exp,
        "deducted_years": 0.0,
        "points_claimable_years": pts_years,
        "points_claimable_points": overseas_pts,
        "points_description": overseas_desc,
        "deemed_skilled_summary": f"{auth_code} · 0.0 yrs deducted · {pts_years:.1f} yrs points-claimable ({overseas_pts} pts)",
        "justification": f"Assessed under {auth_name} guidelines for ANZSCO {code} ({title}). Requires relevant degree/diploma in Social Work or Community Services plus fieldwork practicum.",
        "required_documents": [
            "Passport bio-data page",
            "Degree / Diploma Certificate & Transcripts",
            "Fieldwork placement letter detailing practicum hours (minimum 500-980 hours)",
            "Employment Reference Letters on organization letterhead",
            "Payment Evidence (payslips, tax forms, bank credits)",
            "English Language Test Result",
        ],
        "risk_warnings": [f"{auth_code} requires evidence of supervised student fieldwork hours during qualification."],
        "screening_checklist_notes": "Verify practicum placement hours from educational institution.",
    }


# ══════════════════════════════════════════════════════════════════════════
# ENGINEERS AUSTRALIA (EA) EVALUATION ENGINE
# ══════════════════════════════════════════════════════════════════════════
def evaluate_engineers_australia(
    occ: Dict[str, Any],
    profile: Dict[str, Any],
    qual_level: str,
    field_of_study: str,
    total_exp: float,
    au_exp: float,
) -> Dict[str, Any]:
    """Evaluate candidate profile against Engineers Australia (EA) criteria."""
    code = occ.get("code") or "233512"
    title = occ.get("title") or "Mechanical Engineer"

    is_eng, eng_reason = is_field_relevant_to_occupation(field_of_study, occ)
    q_lower = _normalize_str(qual_level)
    is_degree = any(k in q_lower for k in ["bachelor", "master", "doctorate", "phd", "b.tech", "btech", "b.e.", "be ", "m.tech", "m.e."]) or not q_lower

    if not is_eng:
        return {
            "authority_code": "EA",
            "authority_name": "Engineers Australia",
            "occupation_code": code,
            "occupation_title": title,
            "pathway_name": "Engineers Australia MSA (Accredited Accord or CDR Pathway)",
            "assessment_outcome": "Ineligible / Non-Engineering Qualification",
            "is_positive": False,
            "rpl_required": False,
            "rpl_details": {},
            "total_experience_years": total_exp,
            "deducted_years": 0.0,
            "points_claimable_years": 0.0,
            "points_claimable_points": 0,
            "points_description": "Ineligible for points claim without a positive skills assessment",
            "deemed_skilled_summary": "Ineligible for EA Skills Assessment (Non-Engineering Degree)",
            "justification": (
                f"Assessed by Engineers Australia for ANZSCO {code} ({title}). "
                f"Engineers Australia strictly assesses professional engineers, technologists, and associates who hold recognized tertiary qualifications in engineering. "
                f"Your qualification ({qual_level or 'Tertiary Award'} in '{field_of_study or 'Non-Engineering'}') does not meet the mandatory engineering degree requirement for this occupation. "
                f"Non-engineering qualifications cannot be assessed by Engineers Australia even with substantial work experience."
            ),
            "required_documents": [
                "Passport bio-data page",
                "Degree Certificate and Academic Transcripts in Engineering",
                "3 CDR Career Episodes + Summary Statement + CPD Record (if non-accredited)",
                "Relevant Employment Reference Letters & Payment Evidence",
            ],
            "risk_warnings": [
                "Engineers Australia strictly rejects non-engineering qualifications.",
                "Work experience alone without a tertiary engineering degree cannot substitute for EA educational requirements."
            ],
            "screening_checklist_notes": f"Candidate holds non-engineering qualification ({field_of_study}). Cannot lodge with Engineers Australia.",
        }

    # Candidate holds a recognized engineering qualification
    pts_years = total_exp
    overseas_pts, overseas_desc = calculate_gsm_experience_points(pts_years, in_australia=False)
    return {
        "authority_code": "EA",
        "authority_name": "Engineers Australia",
        "occupation_code": code,
        "occupation_title": title,
        "pathway_name": "Engineers Australia MSA (Accredited Accord or CDR Pathway)",
        "assessment_outcome": "Likely Positive Assessment",
        "is_positive": True,
        "rpl_required": False,
        "rpl_details": {},
        "total_experience_years": total_exp,
        "deducted_years": 0.0,
        "points_claimable_years": pts_years,
        "points_claimable_points": overseas_pts,
        "points_description": overseas_desc,
        "deemed_skilled_summary": f"EA MSA · 0.0 yrs deducted · {pts_years:.1f} yrs claimable ({overseas_pts} pts)",
        "justification": (
            f"Assessed by Engineers Australia for ANZSCO {code} ({title}). "
            f"Candidate holds an engineering qualification ({qual_level or 'Bachelor'} in {field_of_study or 'Engineering'}). "
            "Applicants holding non-accredited engineering degrees must submit a Competency Demonstration Report (CDR) "
            "comprising 3 Career Episodes, Continuing Professional Development (CPD), and a Summary Statement."
        ),
        "required_documents": [
            "Passport bio-data page",
            "Engineering Degree Certificate and Transcripts",
            "3 CDR Career Episodes + Summary Statement + CPD Record (if non-accredited)",
            "Relevant Employment Reference Letters & Payment Evidence (for Relevant Skilled Employment Advice)",
            "English language test result (IELTS 6.0 each / PTE 50 each)",
        ],
        "risk_warnings": [
            "Plagiarism in CDR career episodes results in a mandatory 12-to-36-month ban by Engineers Australia.",
            "Ensure career episodes demonstrate personal engineering contributions (use 'I designed', 'I calculated').",
        ],
        "screening_checklist_notes": "Verify Washington Accord status of university/program or prepare CDR brief.",
    }


# ══════════════════════════════════════════════════════════════════════════
# INSTITUTE OF MANAGERS AND LEADERS (IML / AIM) EVALUATION ENGINE
# ══════════════════════════════════════════════════════════════════════════
def evaluate_iml(
    occ: Dict[str, Any],
    profile: Dict[str, Any],
    qual_level: str,
    field_of_study: str,
    total_exp: float,
    au_exp: float,
) -> Dict[str, Any]:
    """Evaluate candidate profile against Institute of Managers and Leaders (IML / AIM) criteria."""
    code = occ.get("code") or "132111"
    title = occ.get("title") or "Corporate Services Manager"

    pri_app = profile.get("primary_applicant") or {}
    prof_dict = pri_app.get("professional") or {}
    cand_prof = (
        prof_dict.get("current_profession")
        or pri_app.get("current_profession")
        or prof_dict.get("designation")
        or profile.get("current_profession")
        or profile.get("profession")
        or ""
    ).lower()
    wh = pri_app.get("work_history") or profile.get("work_history") or []
    all_titles = [cand_prof] + [(w.get("designation") or w.get("title") or "").lower() for w in wh]
    has_mgr_role = any(any(k in t for k in ["manager", "director", "head of", "chief", "lead", "general manager", "executive"]) for t in all_titles if t)

    required_exp = 3.0
    if not has_mgr_role:
        outcome = "Ineligible / Non-Managerial Career History"
        is_pos = False
        justification = (
            f"Assessed by Institute of Managers and Leaders (IML) for ANZSCO {code} ({title}). "
            f"IML assessment strictly requires candidate to have served in a designated Senior Managerial role (reporting directly to the CEO/Board and supervising subordinate managers). "
            f"Candidate's work history indicates non-managerial employment ({', '.join([t for t in all_titles if t][:2]) or 'non-executive'})."
        )
    elif total_exp < required_exp:
        shortfall = required_exp - total_exp
        outcome = "Ineligible / Managerial Experience Shortfall"
        is_pos = False
        justification = (
            f"Assessed by Institute of Managers and Leaders (IML) for ANZSCO {code} ({title}). "
            f"IML criteria mandate at least 3 years of senior managerial experience with organizational hierarchy evidence (direct reporting line to Board/CEO and subordinate managers). "
            f"Candidate currently has {total_exp:.1f} years total experience (shortfall of {shortfall:.1f} years)."
        )
    else:
        outcome = "Likely Positive Assessment"
        is_pos = True
        justification = (
            f"Assessed by Institute of Managers and Leaders (IML) for ANZSCO {code} ({title}). "
            f"Meets the minimum 3 years managerial requirement. All {total_exp:.1f} years of post-qualification management experience are claimable for GSM points."
        )

    pts_years = total_exp if is_pos else 0.0
    overseas_pts, overseas_desc = calculate_gsm_experience_points(pts_years, in_australia=False)

    return {
        "authority_code": "IML",
        "authority_name": "Institute of Managers and Leaders",
        "occupation_code": code,
        "occupation_title": title,
        "pathway_name": "IML Senior Management Skills Assessment",
        "assessment_outcome": outcome,
        "is_positive": is_pos,
        "rpl_required": False,
        "rpl_details": {},
        "total_experience_years": total_exp,
        "deducted_years": 0.0,
        "points_claimable_years": pts_years,
        "points_claimable_points": overseas_pts,
        "points_description": overseas_desc,
        "deemed_skilled_summary": f"IML Management · 0.0 yrs deducted · {pts_years:.1f} yrs claimable ({overseas_pts} pts)" if is_pos else "Ineligible (Managerial Experience Shortfall)",
        "justification": justification,
        "required_documents": [
            "Passport bio-data page",
            "Degree Certificate & Academic Transcripts",
            "Certified Detailed Organisational Charts showing direct reporting line to Board/CEO and subordinate managers",
            "Employment Reference Letters on company letterhead detailing financial, operational, and staff delegations",
            "Proof of Paid Employment (payslips, tax assessments, bank statements)",
            "Comprehensive Curriculum Vitae / Resume",
        ],
        "risk_warnings": [
            "IML strictly requires verified organizational charts showing leadership authority over professional staff.",
            "Operational / junior supervisors without budget or hiring delegation will be refused."
        ],
        "screening_checklist_notes": "Collect organizational charts and employer reference letters confirming senior management role.",
    }


# ══════════════════════════════════════════════════════════════════════════
# GENERIC DESIGNATED AUTHORITY HANDLER
# ══════════════════════════════════════════════════════════════════════════
def evaluate_generic_authority(
    occ: Dict[str, Any],
    profile: Dict[str, Any],
    qual_level: str,
    field_of_study: str,
    total_exp: float,
    au_exp: float,
    auth_code: str,
    auth_name: str,
) -> Dict[str, Any]:
    code = occ.get("code") or ""
    title = occ.get("title") or ""
    pts_years = total_exp
    overseas_pts, overseas_desc = calculate_gsm_experience_points(pts_years, in_australia=False)

    return {
        "authority_code": auth_code,
        "authority_name": auth_name,
        "occupation_code": code,
        "occupation_title": title,
        "pathway_name": f"{auth_code} Standard Skills Assessment",
        "assessment_outcome": "Likely Positive Assessment",
        "is_positive": True,
        "rpl_required": False,
        "rpl_details": {},
        "total_experience_years": total_exp,
        "deducted_years": 0.0,
        "points_claimable_years": pts_years,
        "points_claimable_points": overseas_pts,
        "points_description": overseas_desc,
        "deemed_skilled_summary": f"{auth_code} · 0.0 yrs deducted · {pts_years:.1f} yrs points-claimable ({overseas_pts} pts)",
        "justification": f"Assessed under official {auth_name} guidelines for ANZSCO {code} ({title}). Post-qualification employment ({total_exp:.1f} yrs) is claimable.",
        "required_documents": [
            "Passport bio-data page",
            "Degree Certificate & Academic Transcripts",
            "Employment Reference Letters detailing occupational duties on employer letterhead",
            "Payment Proof (payslips, tax assessments, bank statements)",
            "Curriculum Vitae / Resume",
        ],
        "risk_warnings": ["Ensure employment is verified as 20+ hours per week and salary payments are evidenced."],
        "screening_checklist_notes": "Collect standard identity, qualification, and payment evidence.",
    }


# ══════════════════════════════════════════════════════════════════════════
# MASTER DISPATCHER FOR ALL OCCUPATIONS & AUTHORITIES
# ══════════════════════════════════════════════════════════════════════════
def evaluate_skills_assessment(
    occ: Dict[str, Any],
    profile: Optional[Dict[str, Any]] = None,
    default_client: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Master evaluator that inspects the occupation and candidate profile,
    dispatches to the correct assessing body engine across all 27+ Australian authorities,
    and returns a comprehensive evaluation report.
    """
    if not occ:
        occ = {}
    if not profile:
        profile = {}

    primary = profile.get("primary_applicant") or profile or {}
    education = primary.get("education") or {}
    if not isinstance(education, dict):
        education = {"highest_qualification": str(education)}
    professional = primary.get("professional") or {}
    if not isinstance(professional, dict):
        professional = {"years_experience_total": professional}

    # Extract qualification & field of study
    qual_level = (
        education.get("highest_qualification")
        or profile.get("qualification")
        or (default_client or {}).get("education")
        or ""
    )
    field_of_study = (
        education.get("field_of_study")
        or profile.get("field_of_study")
        or (default_client or {}).get("field_of_study")
        or ""
    )

    # Extract total & AU experience
    total_exp = _to_float(
        professional.get("years_experience_total")
        or profile.get("years_experience_total")
        or (default_client or {}).get("work_exp_years")
        or profile.get("work_experience")
        or 0.0
    )
    au_exp = _to_float(
        professional.get("years_experience_australia")
        or profile.get("years_experience_australia")
        or 0.0
    )

    # Authority extraction
    auth_val = occ.get("assessing_authority") or occ.get("assessing_body") or {}
    auth_dict = auth_val if isinstance(auth_val, dict) else {}
    if isinstance(auth_val, dict):
        raw_code = str(auth_val.get("code") or auth_val.get("short_name") or occ.get("assessing_authority_code") or "").strip().upper()
        raw_name = str(auth_val.get("name") or raw_code).strip().upper()
    else:
        raw_code = str(auth_val or occ.get("assessing_authority_code") or "").strip().upper()
        raw_name = raw_code
    code = str(occ.get("code") or "").strip()

    # 1. ANMAC (Nursing & Midwifery)
    if (
        raw_code == "ANMAC"
        or "NURSING" in raw_name
        or "MIDWIFERY" in raw_name
        or code.startswith("254")
        or code.startswith("4114")
    ):
        return evaluate_anmac(occ, profile, qual_level, field_of_study, total_exp, au_exp)

    # 2. ACS (Australian Computer Society - ICT)
    elif (
        raw_code == "ACS"
        or "AUSTRALIAN COMPUTER SOCIETY" in raw_name
        or code.startswith("261")
        or code.startswith("262")
        or code.startswith("263")
        or code.startswith("1351")
        or code in ("223211", "313113")
    ):
        is_closely = profile.get("is_closely_related", True)
        it_pct = profile.get("it_percentage")
        return evaluate_acs(occ, profile, qual_level, field_of_study, total_exp, au_exp, is_closely_related=is_closely, it_percentage=it_pct)

    # 3. CPA Australia / CA ANZ / IPA (Accountants & Finance)
    elif (
        raw_code in ("CPA", "CPAA", "CAANZ", "IPA", "CPA AUSTRALIA")
        or "ACCOUNTANT" in raw_name
        or code.startswith("2211")
        or code.startswith("2212")
    ):
        return evaluate_accounting(occ, profile, qual_level, field_of_study, total_exp, au_exp)

    # 4. AITSL (Teachers)
    elif (
        raw_code == "AITSL"
        or "TEACHING" in raw_name
        or "SCHOOL LEADERSHIP" in raw_name
        or code.startswith("241")
    ):
        return evaluate_aitsl(occ, profile, qual_level, field_of_study, total_exp, au_exp)

    # 5. MedBA / AMC (Medical Practitioners & Doctors)
    elif (
        raw_code in ("MEDBA", "AMC")
        or "MEDICAL BOARD" in raw_name
        or code.startswith("253")
    ):
        return evaluate_medba(occ, profile, qual_level, field_of_study, total_exp, au_exp)

    # 6. AASW / ACWA (Social Workers & Community Workers)
    elif (
        raw_code in ("AASW", "ACWA")
        or "COMMUNITY WORKERS" in raw_name
        or "SOCIAL WORKERS" in raw_name
        or code in ("272511", "272613", "411711", "411712")
    ):
        is_aasw = (raw_code == "AASW" or code == "272511")
        return evaluate_acwa_aasw(occ, profile, qual_level, field_of_study, total_exp, au_exp, is_aasw=is_aasw)

    # 7. Engineers Australia (EA)
    elif (
        raw_code in ("EA", "IEAUST")
        or "ENGINEERS AUSTRALIA" in raw_name
        or (code.startswith("233") and raw_code != "TRA" and not occ.get("is_trade_occupation"))
        or code.startswith("3122")
        or code.startswith("3123")
        or code.startswith("3125")
        or code.startswith("2633")
    ):
        return evaluate_engineers_australia(occ, profile, qual_level, field_of_study, total_exp, au_exp)

    # 8. Institute of Managers and Leaders (IML / AIM)
    elif (
        raw_code in ("IML", "AIM")
        or "MANAGERS AND LEADERS" in raw_name
        or code in ("111111", "111211", "131112", "131113", "132111", "132311", "132411", "133111")
    ):
        return evaluate_iml(occ, profile, qual_level, field_of_study, total_exp, au_exp)

    # 9. TRA & Trade Occupations (Trades Recognition Australia)
    elif (
        raw_code == "TRA"
        or "TRADES RECOGNITION" in raw_name
        or bool(occ.get("is_trade_occupation"))
        or bool(occ.get("vetassess_approved_rto"))
    ) and not (code.startswith("254") or code.startswith("241") or code.startswith("261")):
        is_licensed = occ.get("is_licensed_trade", False)
        has_formal = any(k in _normalize_str(qual_level) for k in ["cert", "diploma", "apprenticeship", "trade", "bachelor", "degree"])
        return evaluate_tra_and_trade(occ, profile, qual_level, field_of_study, total_exp, au_exp, is_licensed_trade=is_licensed, has_formal_trade_training=has_formal)

    # 10. VETASSESS Professional Occupations
    elif (
        raw_code in ("VETASSESS", "VET")
        or "VETASSESS" in raw_name
        or "VOCATIONAL EDUCATION" in raw_name
        or bool(occ.get("vetassess_group"))
    ):
        is_hr_major = profile.get("is_highly_relevant_major")
        has_add_qual = profile.get("has_additional_relevant_qual", False)
        return evaluate_vetassess_professional(occ, profile, qual_level, field_of_study, total_exp, au_exp, is_highly_relevant_major=is_hr_major, has_additional_relevant_qual=has_add_qual)

    # 11. All Other Authorities (ASMIRT, NAATI, ADC, APC_Pharm, AACA, OCANZ, AIQS, AIMS, AVBC, ACECQA, SPA, APC, DA, Audiology)
    else:
        authority_label = auth_dict.get("name") or occ.get("assessing_body") or raw_code or "Designated Assessing Authority"
        return evaluate_generic_authority(occ, profile, qual_level, field_of_study, total_exp, au_exp, raw_code or "AUTHORITY", authority_label)

