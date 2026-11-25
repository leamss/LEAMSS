"""AI Sales Communication Assistant Service.

Powers intelligent sales communication across:
  1. WhatsApp (concise, high-conversion chat messages with 1-click composer insertion)
  2. Email (structured, professional proposals, checklists, and replies for GmailComposer)
  3. Live Calls (real-time spoken scripts and quick factual bullet points for the Call Modal)

Grounded in verified Product Master data and Occupation Intelligence across all configured countries.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from bson import ObjectId

from core.database import db, product_master_col, leads_col
from core.occupation_intelligence import (
    detect_occupation_in_query,
    detect_country_and_visa_in_query,
    get_full_occupation_profile,
    get_statutory_fees_and_commercials,
    normalize_country,
)

logger = logging.getLogger(__name__)


async def _fetch_lead_data(lead_id: Optional[str]) -> Dict[str, Any]:
    """Look up lead record from MongoDB by id or _id."""
    if not lead_id:
        return {}
    try:
        q: List[Dict[str, Any]] = [{"id": str(lead_id)}]
        try:
            q.append({"_id": ObjectId(str(lead_id))})
        except Exception:
            pass
        doc = await leads_col.find_one({"$or": q})
        return doc or {}
    except Exception as e:
        logger.warning("Failed to fetch lead %s: %s", lead_id, e)
        return {}


async def _find_product_master_doc(country: str, service: Optional[str] = None, subclass: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Find the most relevant product master record for the target country and service."""
    c_norm = normalize_country(country)
    
    # 1. Match country + subclass
    if subclass:
        doc = await product_master_col.find_one({
            "country": {"$regex": f"^{re.escape(c_norm)}$", "$options": "i"},
            "visa_subclass": {"$regex": f"^{re.escape(subclass)}$", "$options": "i"},
            "is_archived": {"$ne": True}
        })
        if doc:
            return doc

    # 2. Match country + service keyword
    if service:
        # Check visa subclass inside service string (e.g. 189, 190, 491, H-1B, FSW)
        for sc in ["189", "190", "491", "482", "h-1b", "h1b", "fsw", "pnp", "chancenkarte", "blue card", "smc"]:
            if sc in service.lower():
                doc = await product_master_col.find_one({
                    "country": {"$regex": f"^{re.escape(c_norm)}$", "$options": "i"},
                    "visa_subclass": {"$regex": re.escape(sc), "$options": "i"},
                    "is_archived": {"$ne": True}
                })
                if doc:
                    return doc

        doc = await product_master_col.find_one({
            "country": {"$regex": f"^{re.escape(c_norm)}$", "$options": "i"},
            "name": {"$regex": re.escape(service[:20]), "$options": "i"},
            "is_archived": {"$ne": True}
        })
        if doc:
            return doc

    # 3. Match country default
    doc = await product_master_col.find_one({
        "country": {"$regex": f"^{re.escape(c_norm)}$", "$options": "i"},
        "is_archived": {"$ne": True}
    })
    return doc


def _build_deterministic_whatsapp_reply(
    lead_name: str,
    country: str,
    product: Optional[Dict[str, Any]],
    fees: Dict[str, Any],
    intent: str,
    client_message: str,
    profile: Optional[Any],
) -> str:
    """Generates a concise, high-converting WhatsApp message."""
    v_name = product.get("name") if product else f"{country} Skilled Migration"
    sc = product.get("visa_subclass") if product else ""
    sc_label = f" ({sc})" if sc else ""

    if intent == "objection_rebuttal" or any(k in client_message.lower() for k in ["guarantee", "promise", "refund", "risk", "fake"]):
        objs = product.get("objections_rebuttals") or []
        first_rebuttal = objs[0].get("rebuttal") if objs else (
            "Under official immigration law, all visa and PR decisions remain the statutory prerogative of government visa officers. "
            "No migration consultant can legally guarantee visa issuance. What LEAMSS guarantees is 100% institutional compliance, ensuring your paperwork, "
            "skills assessment, points optimization, and employer references conform strictly to official government benchmarks."
        )
        return (
            f"Hello *{lead_name}* 🛡️\n\n"
            f"I completely understand your concern. {first_rebuttal}\n\n"
            f"Our dedicated case processing managers maintain an audited first-time approval track record by ensuring zero procedural flaws. "
            f"Can we schedule a quick 5-minute phone consultation today to review your exact profile and risk factors?\n\n"
            f"_Note: Official visa decisions remain subject to statutory government authority review; LEAMSS does not guarantee approval._"
        )

    elif intent == "fees_costs" or any(k in client_message.lower() for k in ["fee", "cost", "price", "charge", "payment", "package"]):
        return (
            f"Hello *{lead_name}* 👋\n\n"
            f"Here is the transparent statutory fee breakdown for *{country} — {v_name}{sc_label}*:\n\n"
            f"💰 *Official Government Fee:* {fees.get('gov_fee_foreign', 'Variable')} (~{fees.get('gov_fee_inr_approx', 'N/A')})\n"
            f"💼 *LEAMSS Retainer:* {fees.get('leamss_retainer_inr', '₹1,25,000 (+ 18% GST)')}\n"
            f"📌 *Milestone Schedule:* {fees.get('leamss_milestones', '40% Onboarding ➔ 30% Assessment ➔ 30% Lodgement')}\n\n"
            f"All government charges are paid directly to the official immigration portal in transparent stages. Would you like me to share our official proposal and agreement draft?\n\n"
            f"_Note: Official visa decisions remain subject to statutory government authority review; LEAMSS does not guarantee approval._"
        )

    elif any(k in client_message.lower() for k in ["family", "spouse", "partner", "wife", "husband", "child", "children", "kid", "dependent", "marriage"]):
        return (
            f"Hello *{lead_name}* 👨‍👩‍👧\n\n"
            f"Yes, you can include your eligible family members in your *{country} — {v_name}{sc_label}* application:\n\n"
            f"1️⃣ *Eligible Dependents:* Legally married spouse or de facto partner, and dependent children can be included in your application.\n"
            f"2️⃣ *Permanent Residency Approval:* Family members receive PR only if they are included in the application and their visas are approved by the immigration authority.\n"
            f"3️⃣ *Child Age & Dependency:* Children under 18 qualify automatically. Children aged 18 to 23 must be financially dependent (full-time students, unmarried). Children aged 23+ qualify only if dependent due to physical or mental disability.\n"
            f"4️⃣ *Spouse Evidence & Clearances:* Spouses must provide genuine relationship evidence (marriage or 12-month de facto cohabitation), and all family members must satisfy statutory health and character clearances.\n"
            f"5️⃣ *Application Charges:* Additional government visa application charges apply for secondary applicants.\n\n"
            f"Would you like us to evaluate your family unit's eligibility and prepare your consolidated points profile?\n\n"
            f"_Note: Official visa decisions remain subject to statutory government authority review; LEAMSS does not guarantee approval._"
        )

    elif any(k in client_message.lower() for k in ["travel", "abroad", "outside", "offshore", "leave india", "leave country", "visit"]):
        return (
            f"Hello *{lead_name}* ✈️\n\n"
            f"Regarding your question about international travel: You **do not need to travel abroad or travel to {country}** to apply for your *{v_name}{sc_label}*.\n\n"
            f"Under official immigration regulations, skilled migration is a **100% offshore process** completed entirely from your home country. "
            f"Your educational credentials, English test, expression of interest, and visa application are all lodged online from home. "
            f"You only travel to {country} after your permanent resident visa is officially granted.\n\n"
            f"Would you like us to evaluate your profile credentials for offshore lodgement?\n\n"
            f"_Note: Official visa decisions remain subject to statutory government authority review; LEAMSS does not guarantee approval._"
        )

    elif any(k in client_message.lower() for k in ["benefit", "why choose", "advantage", "perk", "medicare", "rights", "why migrate", "why australia", "why canada"]):
        return (
            f"Hello *{lead_name}* 🌟\n\n"
            f"Securing Permanent Residency in *{country}* under the *{v_name}{sc_label}* grants you and your family exceptional advantages:\n\n"
            f"1️⃣ *Unconditional Settlement & Work Rights:* Live, work, and operate a business anywhere across {country}.\n"
            f"2️⃣ *Universal Healthcare:* Subsidized or comprehensive medical cover under national healthcare programs.\n"
            f"3️⃣ *Direct Pathway to Citizenship:* Eligible to apply for full passport and citizenship after qualifying residency.\n"
            f"4️⃣ *Family Privileges & Free Education:* Sponsor eligible family members and access free public schooling for your children.\n\n"
            f"Would you like us to run a free eligibility points calculation for you and your family today?\n\n"
            f"_Note: Official visa decisions remain subject to statutory government authority review; LEAMSS does not guarantee approval._"
        )

    elif intent == "document_checklist" or any(k in client_message.lower() for k in ["document", "doc", "paper", "checklist", "resume"]):
        checklist = product.get("document_checklist_template") or [
            "Valid Passport (all pages)",
            "Degree Transcripts & Graduation Certificates",
            "Experience Letters & Relieving Letters on Letterhead",
            "Salary Bank Statements & Form 16 / Tax Returns",
            "English Language Test Scorecard (IELTS / PTE / TOEFL)",
        ]
        items_text = "\n".join([f"• {item}" for item in checklist[:5]])
        return (
            f"Hello *{lead_name}* 📄\n\n"
            f"To initiate your *{country} {v_name}* application, our legal team requires the following initial documents for assessment:\n\n"
            f"{items_text}\n\n"
            f"You can send your updated CV and degree certificates right here on WhatsApp, and we will conduct your preliminary credential evaluation within 24 hours. Does that work for you?"
        )

    elif intent == "eligibility" or any(k in client_message.lower() for k in ["eligib", "qualif", "points", "score", "pass mark", "teer", "anzsco"]):
        pts = fees.get("statutory_benchmark", "Official points & qualification criteria.")
        occ_detail = f" Your target occupation aligns with *{profile.title}* ({profile.code} - {profile.skill_tier_label})." if profile else ""
        return (
            f"Hello *{lead_name}* 📊\n\n"
            f"For *{country} — {v_name}{sc_label}*, eligibility is evaluated across age, formal degree equivalence, relevant work experience, and English test scores (IELTS/PTE).{occ_detail}\n\n"
            f"📌 *Official Pass Mark Benchmark:* {pts}\n\n"
            f"May I ask your exact age and the number of years of post-graduation experience you hold? I can run an immediate points calculation for you right now!"
        )

    elif intent == "objection_rebuttal" or any(k in client_message.lower() for k in ["guarantee", "refund", "time", "delay", "risk", "fake"]):
        objs = product.get("objections_rebuttals") or []
        first_rebuttal = objs[0].get("rebuttal") if objs else (
            "Under official immigration law, all visa and PR decisions remain the statutory prerogative of government visa officers. "
            "No migration consultant can legally guarantee visa issuance. What LEAMSS guarantees is 100% institutional compliance, ensuring your paperwork, "
            "skills assessment, points optimization, and employer references conform strictly to official government benchmarks."
        )
        return (
            f"Hello *{lead_name}* 🛡️\n\n"
            f"I completely understand your concern. {first_rebuttal}\n\n"
            f"Our dedicated case processing managers maintain an audited first-time approval track record by ensuring zero procedural flaws. "
            f"Can we schedule a quick 5-minute phone consultation today to review your exact profile and risk factors?"
        )

    elif intent == "process_steps" or any(k in client_message.lower() for k in ["process", "step", "how it works", "procedure", "timeline"]):
        return (
            f"Hello *{lead_name}* 🚀\n\n"
            f"Here is the streamlined 4-step roadmap for your *{country} {v_name}*:\n\n"
            f"1️⃣ *Profile Audit & Credential Assessment:* Educational equivalency & skills authority verification.\n"
            f"2️⃣ *Expression of Interest (EOI):* Lodging your profile in the federal/state selection pool.\n"
            f"3️⃣ *Invitation to Apply (ITA) & Nomination:* Securing statutory invitation.\n"
            f"4️⃣ *Final Visa Lodgement:* Submitting complete biometrics, medicals, and police clearance to the government.\n\n"
            f"The entire process typically spans 6 to 12 months depending on the draw schedule. When would be a good time for a brief call to start step 1?"
        )

    # General auto-reply
    elevator = (product.get("sales_playbook") or {}).get("elevator_pitch") or f"Legal permanent settlement and work authorization in {country} under official {v_name} criteria."
    return (
        f"Hello *{lead_name}* 👋\n\n"
        f"Thank you for contacting LEAMSS Immigration Consulting regarding *{country} — {v_name}{sc_label}*.\n\n"
        f"{elevator}\n\n"
        f"Our team of licensed immigration advisors is reviewing your profile to structure the highest-probability pathway for you and your family. "
        f"Could you please share your updated CV/resume so we can initiate your points and credential evaluation?"
    )


def _build_deterministic_email_reply(
    lead_name: str,
    country: str,
    product: Optional[Dict[str, Any]],
    fees: Dict[str, Any],
    intent: str,
    client_message: str,
    profile: Optional[Any],
) -> Dict[str, str]:
    """Generates a structured, professional email response."""
    v_name = product.get("name") if product else f"{country} Skilled Migration"
    sc = product.get("visa_subclass") if product else ""
    sc_label = f" (Subclass: {sc})" if sc else ""
    auth = product.get("authority_name") if product else f"Immigration Authority of {country}"
    portal = fees.get("official_portal", "https://leamss.com/atlas/")

    subject = f"LEAMSS Immigration: Comprehensive {country} {v_name} Advisory for {lead_name}"

    checklist_items = product.get("document_checklist_template") or [
        "Color scan of Passport (valid for at least 12 months)",
        "Degree Certificates & Official University Transcripts",
        "Detailed Experience Letters on Official Company Letterhead",
        "Salary Bank Statements & Tax Documentation (Form 16 / ITR)",
        "Official English Language Test Results (IELTS / PTE Academic)",
    ]
    docs_block = "\n".join([f"  • {d}" for d in checklist_items[:5]])

    body = (
        f"Dear {lead_name},\n\n"
        f"Thank you for reaching out to LEAMSS Immigration Consulting. We have reviewed your inquiry regarding skilled immigration to {country} under the {v_name}{sc_label}.\n\n"
        f"### 📌 1. Pathway & Regulatory Framework\n"
        f"- Destination: {country}\n"
        f"- Target Visa Category: {v_name}{sc_label}\n"
        f"- Administering Authority: {auth}\n"
        f"- Benchmark Requirement: {fees.get('statutory_benchmark', 'Standard points-tested criteria')}\n"
    )

    if profile:
        body += (
            f"- Nominated Occupation: {profile.title} ({profile.code})\n"
            f"- Classification Tier: {profile.skill_tier_label}\n"
            f"- Designated Assessing Body: {profile.assessing_authority}\n"
        )

    is_fee_query = intent == "fees_costs" or any(k in client_message.lower() for k in ["fee", "cost", "price", "charge", "payment", "package", "how much"])
    is_family_query = any(k in client_message.lower() for k in ["family", "spouse", "partner", "wife", "husband", "child", "children", "kid", "dependent", "marriage"])
    is_travel_query = any(k in client_message.lower() for k in ["travel", "abroad", "outside", "offshore", "leave india", "leave country", "visit"])
    is_benefits_query = any(k in client_message.lower() for k in ["benefit", "why choose", "advantage", "perk", "medicare", "rights", "why migrate"])

    if is_family_query and not is_fee_query:
        body += (
            f"\n### 👨‍👩‍👧 2. Family Inclusion & Secondary Applicant Regulations\n"
            f"- Eligible Family Members: Legally married spouse or de facto partner and dependent children can be included in your {v_name}{sc_label} application.\n"
            f"- Permanent Residency Approval Condition: Family members receive Permanent Residency only if they are included in the application and their visas are approved by {auth}.\n"
            f"- Dependent Children Age Limits: Children under 18 qualify automatically; children aged 18 to 23 must be financially dependent (full-time students, unmarried); children aged 23+ qualify only if incapacitated due to physical or mental disability.\n"
            f"- Spouse Genuine Relationship Evidence: Genuine and continuing relationship evidence is mandatory (marriage certificate or minimum 12-month de facto cohabitation).\n"
            f"- Mandatory Health & Character: All included secondary applicants must pass official immigration health exams and police character clearances.\n"
            f"- Statutory Application Charges: Additional government visa application charges apply for secondary applicants.\n\n"
        )
    elif is_travel_query and not is_fee_query:
        body += (
            f"\n### ✈️ 2. Offshore Application & International Travel Regulations\n"
            f"- 100% Offshore Application: Under official {auth} regulations, General Skilled Migration is completed from your home country without international travel.\n"
            f"- Zero Foreign Travel Prerequisite: You do not need to travel abroad or travel to {country} to apply for or secure your PR visa.\n"
            f"- Home Country Testing & Lodgement: Skills assessment, language tests, and government lodgement are executed online from home.\n"
            f"- Initial Entry Requirement: Travel to {country} is only required after your permanent residency visa is officially granted by {auth}.\n\n"
        )
    elif is_benefits_query and not is_fee_query:
        body += (
            f"\n### 🌟 2. Key Permanent Residency Benefits & Entitlements\n"
            f"- Unconditional Work & Settlement Rights: Live, work, and operate a business anywhere across {country} with full statutory protections.\n"
            f"- Universal Healthcare Protection: Subsidized or comprehensive medical cover under national healthcare systems.\n"
            f"- Direct Pathway to Citizenship: Eligible to apply for sovereign citizenship and passport after statutory residence.\n"
            f"- Family Sponsorship Privileges: Sponsor eligible family members and access free public schooling for your children.\n\n"
        )
    else:
        body += (
            f"\n### 💰 2. Official Statutory Fees & Commercial Investment\n"
            f"- Official Government Visa Fee: {fees.get('gov_fee_foreign', 'Variable')} (~{fees.get('gov_fee_inr_approx', 'N/A')})\n"
            f"  (Breakdown: {fees.get('gov_fee_breakdown', 'Standard primary and dependent applicant government fees')})\n"
            f"- LEAMSS Professional Retainer: {fees.get('leamss_retainer_inr', '₹1,25,000 (+ 18% GST)')}\n"
            f"- Transparent Milestone Tranches: {fees.get('leamss_milestones', '40% Retainer ➔ 30% Assessment ➔ 30% Lodgement')}\n"
            f"- Required Settlement Reserve: {fees.get('settlement_funds', 'National statutory requirement')}\n\n"
        )

    body += (
        f"### 📄 3. Initial Documents Required for Evaluation\n"
        f"To proceed with your formal credential assessment and profile points optimization, please provide:\n"
        f"{docs_block}\n\n"
        f"### ⏭️ 4. Recommended Next Steps\n"
        f"We invite you to reply directly to this email with your updated resume, or schedule a dedicated telephone consultation with our senior legal case manager.\n\n"
        f"Official Reference Portal: {portal}\n\n"
        f"Warm regards,\n\n"
        f"**LEAMSS Sales & Advisory Team**\n"
        f"LEAMSS Immigration Consulting | Institutional Compliance\n"
        f"*Disclaimer: Immigration regulations, quotas, and statutory fees are subject to official government gazette updates. LEAMSS operates strictly under licensed compliance and does not guarantee visa issuance.*"
    )

    return {"subject": subject, "body": body}


def _build_deterministic_live_call_copilot(
    lead_name: str,
    country: str,
    product: Optional[Dict[str, Any]],
    fees: Dict[str, Any],
    intent: str,
    client_message: str,
    profile: Optional[Any],
) -> Dict[str, Any]:
    """Generates verbal speaking script and factual bullet points for live call console."""
    v_name = product.get("name") if product else f"{country} Skilled Migration"
    sc = product.get("visa_subclass") if product else ""
    auth = product.get("authority_name") if product else f"Immigration Authority of {country}"

    is_objection = intent == "objection_rebuttal" or any(k in client_message.lower() for k in ["guarantee", "promise", "refund", "risk", "fake"])
    is_fee_query = intent == "fees_costs" or any(k in client_message.lower() for k in ["fee", "cost", "price", "charge", "payment", "package", "how much"])
    is_family_query = any(k in client_message.lower() for k in ["family", "spouse", "partner", "wife", "husband", "child", "children", "kid", "dependent", "marriage"])
    is_travel_query = any(k in client_message.lower() for k in ["travel", "abroad", "outside", "offshore", "leave india"])
    is_benefits_query = any(k in client_message.lower() for k in ["benefit", "why choose", "advantage", "perk", "medicare", "rights"])

    if is_objection:
        speaking_script = (
            f"\"Under official immigration law, all visa and PR decisions remain the statutory prerogative of government visa officers, {lead_name}. "
            f"No licensed migration consultant can legally guarantee visa approval. What LEAMSS guarantees is 100% institutional compliance, ensuring "
            f"your documentation, credential assessment, and petition conform strictly to official government benchmarks.\""
        )
        talking_points = [
            f"Sovereign Authority Prerogative: Only government visa officers approve visas",
            f"LEAMSS Compliance Guarantee: Zero procedural errors and flawless documentation",
            f"Statutory milestone schedule aligned with government approval stages",
        ]
    elif is_family_query and not is_fee_query:
        speaking_script = (
            f"\"Yes, you can include your spouse and dependent children in your {country} {v_name} application, {lead_name}. "
            f"They receive Permanent Residency only if they are included in the application and their visas are approved. "
            f"Dependent children must be under 18, or aged 18 to 23 and financially dependent. Your spouse requires genuine relationship evidence, "
            f"and all applicants must pass health and character checks. Additional government charges apply for secondary applicants.\""
        )
        talking_points = [
            f"Eligible Dependents: Spouse or de facto partner & dependent children",
            f"PR Condition: Granted only if included in application and approved by {auth}",
            f"Child Criteria: Under 18 automatic; 18-23 financially dependent; 23+ disability only",
            f"Compliance: Genuine relationship proof, health exams & police character checks",
            f"Application Charges: Additional government visa charges apply for secondary applicants",
        ]
    elif is_travel_query and not is_fee_query:
        speaking_script = (
            f"\"You do not need to travel abroad or travel to {country} to apply for your {v_name}, {lead_name}. "
            f"Under official {auth} regulations, General Skilled Migration is a 100% offshore process completed entirely from your home country. "
            f"You only travel to {country} after your permanent residency visa is approved by the government.\""
        )
        talking_points = [
            f"100% Offshore Application from home country",
            f"Zero international travel needed to apply or secure PR",
            f"Skills assessment, English tests & visa lodgement handled online",
            f"Initial entry required only after official visa grant",
        ]
    elif is_benefits_query and not is_fee_query:
        speaking_script = (
            f"\"{country} permanent residency provides you and your family with world-class security and rights, {lead_name}. "
            f"You receive unconditional rights to work anywhere, state-funded healthcare, free schooling for your children, "
            f"and a direct pathway to sovereign citizenship and passport.\""
        )
        talking_points = [
            f"Unconditional Work & Settlement Rights across {country}",
            f"Universal healthcare protection & subsidized hospital cover",
            f"Free public schooling for dependent children",
            f"Direct pathway to sovereign citizenship and passport",
        ]
    elif is_fee_query:
        speaking_script = (
            f"\"For {country} {v_name}, all official government charges are paid directly to {auth} in transparent stages, {lead_name}. "
            f"The primary government fee is {fees.get('gov_fee_foreign')} (approx {fees.get('gov_fee_inr_approx')}). "
            f"Our consulting retainer is structured across three milestones aligned with your approval stages.\""
        )
        talking_points = [
            f"Government Fee: {fees.get('gov_fee_foreign')} (~{fees.get('gov_fee_inr_approx')})",
            f"LEAMSS Retainer: {fees.get('leamss_retainer_inr')}",
            f"Milestones: {fees.get('leamss_milestones')}",
            f"Settlement Reserve: {fees.get('settlement_funds')}",
        ]
    else:
        speaking_script = (
            f"\"Thank you for asking, {lead_name}. Under official {country} regulations for the {v_name}, "
            f"your pathway is structured around your formal qualification evaluation and verified post-graduation employment. "
            f"Our legal team prepares your petition to maximize your points score and ensure zero procedural refusals.\""
        )
        talking_points = [
            f"Target Pathway: {country} — {v_name} {f'({sc})' if sc else ''}",
            f"Pass Mark Benchmark: {fees.get('statutory_benchmark')}",
            f"Settlement Funds: {fees.get('settlement_funds')}",
        ]

    if profile:
        talking_points.append(f"Occupation: {profile.title} ({profile.code}) — {profile.skill_tier_label}")
        talking_points.append(f"Assessing Body: {profile.assessing_authority}")

    return {
        "speaking_script": speaking_script,
        "talking_points": talking_points,
    }


async def generate_communication_reply(
    channel: str,
    client_message: str,
    lead_id: Optional[str] = None,
    target_country: Optional[str] = None,
    service_interested: Optional[str] = None,
    intent_type: str = "auto_reply",
    lead_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generates a tailored, channel-specific response grounded in Product Master data."""
    chan = (channel or "whatsapp").lower().strip()
    q = (client_message or "").strip()

    # 1. Fetch lead record if lead_id is provided
    lead = await _fetch_lead_data(lead_id)
    if lead_context and isinstance(lead_context, dict):
        lead = {**lead, **lead_context}

    lead_name = lead.get("name") or "Valued Client"
    raw_country = target_country or lead.get("country_of_interest") or lead.get("interested_country") or lead.get("country") or "Canada"
    raw_service = service_interested or lead.get("service_interested") or lead.get("service") or lead.get("interested_program") or ""

    # 2. Check query-level country and visa intent, and occupation code
    intent = detect_country_and_visa_in_query(q, fallback_country=raw_country, fallback_subclass=raw_service)
    det = detect_occupation_in_query(q, intent.detected_country)
    profile = get_full_occupation_profile(det) if det else None

    # Country resolution (query country overrides mismatched context)
    resolved_country = det.country if (det and det.is_mismatch) else intent.detected_country
    target_subclass = intent.detected_subclass or raw_service

    # 3. Look up matching Product Master record
    product = await _find_product_master_doc(resolved_country, target_subclass)
    subclass = (product.get("visa_subclass") if product else None) or intent.detected_subclass
    fees = get_statutory_fees_and_commercials(resolved_country, subclass)

    # 4. Attempt online Perplexity Sonar generation
    try:
        from core.perplexity_client import call_perplexity

        # Prepare rich grounding context
        doc_context = (
            f"Ground Truth Product Master Data:\n"
            f"- Country: {resolved_country}\n"
            f"- Product: {product.get('name') if product else 'Skilled Migration'} (Subclass: {subclass or 'N/A'})\n"
            f"- Authority: {product.get('authority_name') if product else 'Statutory Immigration Department'}\n"
            f"- Benchmark Pass Mark: {fees.get('statutory_benchmark')}\n"
        )
        if intent.query_topic == "fees":
            doc_context += (
                f"- Official Government Fees: {fees.get('gov_fee_foreign')} (~{fees.get('gov_fee_inr_approx')})\n"
                f"- LEAMSS Retainer: {fees.get('leamss_retainer_inr')}\n"
                f"- Milestones: {fees.get('leamss_milestones')}\n"
                f"- Settlement Funds: {fees.get('settlement_funds')}\n"
            )
        if intent.is_travel_abroad_pr_query and intent.offshore_onshore_explanation:
            doc_context += f"- Statutory Offshore Travel Rule: {intent.offshore_onshore_explanation}\n"
        if profile:
            doc_context += (
                f"- Nominated Occupation: {profile.title} (Code: {profile.code})\n"
                f"- Classification Tier: {profile.skill_tier_label}\n"
                f"- Assessing Body: {profile.assessing_authority}\n"
                f"- Statutory Wage: {profile.statutory_salary_threshold}\n"
            )

        # Context-aware talking points
        if intent.query_topic == "benefits":
            default_talking_points = [
                "Unconditional Work & Settlement Rights across destination country",
                "Universal Healthcare Protection & Subsidized Medical Cover",
                "Direct Pathway to Sovereign Citizenship & Passport",
                "Family Sponsorship Privileges for Spouse and Children",
            ]
        elif intent.query_topic == "travel":
            default_talking_points = [
                "100% Offshore Application from Home Country",
                "Zero Foreign Travel Required to Apply or Secure PR",
                "Skills Assessment, English Test & Visa Lodgement Handled Online",
                "Travel Abroad Required Only After Official Visa Grant",
            ]
        elif intent.query_topic == "fees":
            default_talking_points = [
                f"Official Govt Fee: {fees.get('gov_fee_foreign')}",
                f"LEAMSS Retainer: {fees.get('leamss_retainer_inr')}",
                f"Milestones: {fees.get('leamss_milestones')}",
            ]
        else:
            default_talking_points = [
                f"Pass Mark Benchmark: {fees.get('statutory_benchmark')}",
                f"Target Pathway: {resolved_country} — {product.get('name') if product else 'Skilled Visa'}",
                "Direct Skilled PR without Job Offer",
            ]

        if chan == "whatsapp":
            system_msg = (
                "You are an expert immigration sales assistant generating a ready-to-send WhatsApp reply for a prospective client. "
                "Answer strictly and exclusively what the client asks. DO NOT provide government fees or pricing unless asked. "
                "Keep it concise, warm, professional, and formatted in WhatsApp markdown (*bold*, bullet points, polite emojis). "
                "Maximum 150-200 words. Always answer accurately using the verified Product Master ground truth. "
                "End with a low-friction question or call to action. Never guarantee visa/PR approval."
            )
            prompt = (
                f"Client Name: {lead_name}\n"
                f"Target Country: {resolved_country}\n"
                f"Client Query / WhatsApp Message: {q}\n"
                f"Intent Type: {intent_type}\n"
                f"Topic: {intent.query_topic}\n"
                f"{doc_context}\n"
                f"Generate a polite, punchy, ready-to-send WhatsApp reply strictly answering the client's question."
            )
            raw_answer, model_used = await call_perplexity(prompt, system_msg, model="sonar", max_tokens=600, temperature=0.2, timeout=25.0)
            clean_reply = raw_answer.strip()
            clean_reply = re.sub(r"\n*[_*]*Sources(?:\s*\(.*?\))?:?[_*]*\s*\n+(?:[-*]\s*https?://\S+\n*)+", "", clean_reply, flags=re.IGNORECASE).strip()
            clean_reply = re.sub(r"\n+(?:[-*]\s*https?://\S+\s*)+$", "", clean_reply).strip()
            if not any(k in clean_reply.lower() for k in ["guarantee", "disclaimer", "subject to"]):
                clean_reply += "\n\n_Note: Official visa decisions remain subject to statutory government authority review; LEAMSS does not guarantee approval._"

            return {
                "success": True,
                "status": "success",
                "channel": "whatsapp",
                "reply_text": clean_reply,
                "suggested_text": clean_reply,
                "subject": None,
                "talking_points": default_talking_points,
                "product_matched": {
                    "country": resolved_country,
                    "name": product.get("name") if product else f"{resolved_country} Skilled Visa",
                    "visa_subclass": subclass,
                    "authority": product.get("authority_name") if product else "Official Authority",
                    "government_costs": fees.get("gov_fee_foreign"),
                    "service_price": product.get("service_price") if product else 125000,
                },
                "intent_type": intent_type,
                "model": model_used,
            }

        elif chan == "email":
            system_msg = (
                "You are an expert immigration advisor drafting a professional sales email reply to a prospective client. "
                "Answer strictly and exclusively what the client asks. DO NOT provide government fees or commercial breakdowns unless asked. "
                "Structure it clearly with a professional greeting, concise explanatory paragraphs, "
                "next steps call to action, and professional signoff. Never guarantee visa/PR approval."
            )
            prompt = (
                f"Client Name: {lead_name}\n"
                f"Target Country: {resolved_country}\n"
                f"Client Inquiry / Email: {q}\n"
                f"Intent Type: {intent_type}\n"
                f"Topic: {intent.query_topic}\n"
                f"{doc_context}\n"
                f"Provide: 1) Subject Line: ... 2) Body: ... formatted cleanly for email."
            )
            raw_answer, model_used = await call_perplexity(prompt, system_msg, model="sonar", max_tokens=1000, temperature=0.2, timeout=30.0)

            # Extract subject if present
            subj_match = re.search(r"Subject(?:\s*Line)?:\s*(.+)", raw_answer, re.IGNORECASE)
            subject = subj_match.group(1).strip() if subj_match else f"LEAMSS Consultation: {resolved_country} Migration Guidance for {lead_name}"
            clean_body = re.sub(r"^Subject(?:\s*Line)?:\s*.+\n+", "", raw_answer, flags=re.IGNORECASE).strip()
            clean_body = re.sub(r"\n*[_*]*Sources(?:\s*\(.*?\))?:?[_*]*\s*\n+(?:[-*]\s*https?://\S+\n*)+", "", clean_body, flags=re.IGNORECASE).strip()
            clean_body = re.sub(r"\n+(?:[-*]\s*https?://\S+\s*)+$", "", clean_body).strip()
            if not any(k in clean_body.lower() for k in ["guarantee", "disclaimer", "subject to"]):
                clean_body += "\n\n*Disclaimer: Immigration regulations and statutory fees are subject to official government updates. LEAMSS does not guarantee visa issuance.*"

            return {
                "success": True,
                "status": "success",
                "channel": "email",
                "reply_text": clean_body,
                "suggested_text": clean_body,
                "subject": subject,
                "talking_points": default_talking_points,
                "product_matched": {
                    "country": resolved_country,
                    "name": product.get("name") if product else f"{resolved_country} Skilled Visa",
                    "visa_subclass": subclass,
                    "authority": product.get("authority_name") if product else "Official Authority",
                    "government_costs": fees.get("gov_fee_foreign"),
                    "service_price": product.get("service_price") if product else 125000,
                },
                "intent_type": intent_type,
                "model": model_used,
            }

        elif chan == "live_call":
            system_msg = (
                "You are a real-time sales phone copilot for an immigration consultant on an active client phone call. "
                "The consultant needs an immediate, confident, conversational verbal script to say OUT LOUD to the client, "
                "plus 3-4 factual bullet points (fees, points, timelines). Keep the speaking script to 2-3 sentences max."
            )
            prompt = (
                f"Client Name: {lead_name}\n"
                f"Target Country: {resolved_country}\n"
                f"Client Asked on Phone: {q}\n"
                f"{doc_context}\n"
                f"Format as:\n"
                f"SPEAKING_SCRIPT: <what consultant says on phone>\n"
                f"KEY_FACTS:\n- <fact 1>\n- <fact 2>\n- <fact 3>"
            )
            raw_answer, model_used = await call_perplexity(prompt, system_msg, model="sonar", max_tokens=600, temperature=0.2, timeout=20.0)

            script_match = re.search(r"SPEAKING_SCRIPT:\s*(.+?)(?=KEY_FACTS:|$)", raw_answer, re.DOTALL | re.IGNORECASE)
            speaking_script = script_match.group(1).strip() if script_match else raw_answer.strip()
            speaking_script = speaking_script.strip('"').strip("'")

            facts_match = re.search(r"KEY_FACTS:\s*(.+)", raw_answer, re.DOTALL | re.IGNORECASE)
            facts_lines = [line.strip("- *•").strip() for line in (facts_match.group(1) if facts_match else "").split("\n") if line.strip("- *•").strip()]
            if not facts_lines:
                facts_lines = [
                    f"Govt Fee: {fees.get('gov_fee_foreign')}",
                    f"LEAMSS Retainer: {fees.get('leamss_retainer_inr')}",
                    f"Pass Mark: {fees.get('statutory_benchmark')}",
                ]

            return {
                "success": True,
                "status": "success",
                "channel": "live_call",
                "reply_text": speaking_script,
                "suggested_text": speaking_script,
                "speaking_script": speaking_script,
                "subject": None,
                "talking_points": facts_lines[:5],
                "product_matched": {
                    "country": resolved_country,
                    "name": product.get("name") if product else f"{resolved_country} Skilled Visa",
                    "visa_subclass": subclass,
                    "authority": product.get("authority_name") if product else "Official Authority",
                    "government_costs": fees.get("gov_fee_foreign"),
                    "service_price": product.get("service_price") if product else 125000,
                },
                "intent_type": intent_type,
                "model": model_used,
            }

    except Exception as e:
        logger.warning("Online AI generation failed or timed out; falling back to deterministic synthesis: %s", e)

    # 5. Fallback deterministic generation
    if chan == "whatsapp":
        reply = _build_deterministic_whatsapp_reply(lead_name, resolved_country, product, fees, intent_type, q, profile)
        return {
            "success": True,
            "status": "success",
            "channel": "whatsapp",
            "reply_text": reply,
            "suggested_text": reply,
            "subject": None,
            "talking_points": [
                f"Govt Fee: {fees.get('gov_fee_foreign')}",
                f"Retainer: {fees.get('leamss_retainer_inr')}",
                f"Pass Mark: {fees.get('statutory_benchmark')}",
            ],
            "product_matched": {
                "country": resolved_country,
                "name": product.get("name") if product else f"{resolved_country} Skilled Visa",
                "visa_subclass": subclass,
                "authority": product.get("authority_name") if product else "Official Authority",
                "government_costs": fees.get("gov_fee_foreign"),
                "service_price": product.get("service_price") if product else 125000,
            },
            "intent_type": intent_type,
            "model": "leamss-crm-deterministic-v1",
        }

    elif chan == "email":
        res_email = _build_deterministic_email_reply(lead_name, resolved_country, product, fees, intent_type, q, profile)
        return {
            "success": True,
            "status": "success",
            "channel": "email",
            "reply_text": res_email["body"],
            "suggested_text": res_email["body"],
            "subject": res_email["subject"],
            "talking_points": [
                f"Govt Fee: {fees.get('gov_fee_foreign')}",
                f"Retainer: {fees.get('leamss_retainer_inr')}",
                f"Pass Mark: {fees.get('statutory_benchmark')}",
            ],
            "product_matched": {
                "country": resolved_country,
                "name": product.get("name") if product else f"{resolved_country} Skilled Visa",
                "visa_subclass": subclass,
                "authority": product.get("authority_name") if product else "Official Authority",
                "government_costs": fees.get("gov_fee_foreign"),
                "service_price": product.get("service_price") if product else 125000,
            },
            "intent_type": intent_type,
            "model": "leamss-crm-deterministic-v1",
        }

    else:  # live_call
        call_res = _build_deterministic_live_call_copilot(lead_name, resolved_country, product, fees, intent_type, q, profile)
        return {
            "success": True,
            "status": "success",
            "channel": "live_call",
            "reply_text": call_res["speaking_script"],
            "suggested_text": call_res["speaking_script"],
            "speaking_script": call_res["speaking_script"],
            "subject": None,
            "talking_points": call_res["talking_points"],
            "product_matched": {
                "country": resolved_country,
                "name": product.get("name") if product else f"{resolved_country} Skilled Visa",
                "visa_subclass": subclass,
                "authority": product.get("authority_name") if product else "Official Authority",
                "government_costs": fees.get("gov_fee_foreign"),
                "service_price": product.get("service_price") if product else 125000,
            },
            "intent_type": intent_type,
            "model": "leamss-crm-deterministic-v1",
        }
