"""Product Master AI Research Service.

Researches official government immigration websites and LEAMSS migrate pages
using Perplexity AI with web search (sonar-pro / sonar) to auto-generate
and structure complete Product Master entries for Admin.

Complies with Developer Brief v2.2 Module A specifications:
- Structured Eligibility (Mandatory, Optional, Points-based)
- Visa conditions
- Government costs with line items and currency
- Processing timelines
- Sales Playbook (pitch points, key advantages, target clients)
- Objections & Rebuttals library
- FAQs
- Document Checklist Template
- Official source allowlist
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import httpx

from core.perplexity_client import call_perplexity

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert immigration intelligence assistant for LEAMSS Immigration Portal.
Your task is to conduct accurate, up-to-date research on official government immigration websites and synthesize a complete, production-ready Product Master definition for a specific visa.

CRITICAL INSTRUCTIONS:
1. ONLY cite and use verified information from official government sources (e.g., Australian Department of Home Affairs, Immigration Refugees and Citizenship Canada, UK Visas and Immigration, US CIS, Schengen consulates, or assessing authorities like ACS, VETASSESS, Engineers Australia).
2. Never invent fees, form numbers, point thresholds, or requirements. If a fee or processing time is not officially published or varies, state the verified range or base fee and cite the official URL.
3. Output MUST be valid, raw JSON only. Do not wrap in markdown quotes or extra conversational text.

Output JSON Schema:
{
  "name": "Full Visa Name (e.g. Australia Skilled Independent Visa (Subclass 189))",
  "summary": "Clear, concise 2-3 sentence overview of this visa and who it is for.",
  "visa_type": "Permanent Residency | Work | Study | Visitor / Tourist | Business | Family",
  "visa_subclass": "e.g. 189 or 482 or Express Entry FSW",
  "official_urls": ["https://..."],
  "official_domains": ["immi.homeaffairs.gov.au"],
  "migrate_page_url": "https://leamss.com/migrate/...",
  "eligibility_criteria": {
    "mandatory": [
      {"criterion": "Age under 45 at invitation", "description": "Must be invited before turning 45 years of age."},
      {"criterion": "Competent English", "description": "IELTS 6 each band, PTE 50 each band, or equivalent."}
    ],
    "optional": [
      {"criterion": "Partner skills", "description": "Partner satisfies age, English, and skills requirement for 10 points."}
    ],
    "points_based": {
      "is_points_tested": true,
      "minimum_points": 65,
      "scoring_factors": [
        {"factor": "Age", "max_points": 30, "details": "25-32 years = 30 pts"},
        {"factor": "English", "max_points": 20, "details": "Superior = 20 pts, Proficient = 10 pts"},
        {"factor": "Qualifications", "max_points": 20, "details": "Doctorate = 20, Bachelor/Master = 15"},
        {"factor": "Work Experience", "max_points": 20, "details": "Overseas up to 15 pts, Australian up to 20 pts"}
      ]
    }
  },
  "visa_conditions": [
    "Permanent residency status from date of grant",
    "Full working and study rights in destination country",
    "Access to public health care (e.g. Medicare)",
    "Eligible for citizenship after statutory residency period"
  ],
  "government_costs": {
    "currency": "AUD",
    "exchange_rate_to_inr": 55.0,
    "line_items": [
      {
        "applicant_type": "Primary Applicant",
        "amount": 4765,
        "currency": "AUD",
        "inr_approx": 262075,
        "notes": "Department visa application charge"
      },
      {
        "applicant_type": "Adult Secondary Applicant (18+)",
        "amount": 2385,
        "currency": "AUD",
        "inr_approx": 131175,
        "notes": "Per adult dependent"
      },
      {
        "applicant_type": "Child Secondary Applicant (under 18)",
        "amount": 1195,
        "currency": "AUD",
        "inr_approx": 65725,
        "notes": "Per child dependent"
      }
    ],
    "effective_date": "2025-07-01",
    "source_link": "https://..."
  },
  "processing_timeline": {
    "standard_duration": "6 - 12 months",
    "stages": [
      {"stage": "Skills Assessment", "duration": "2 - 3 months"},
      {"stage": "EOI Submission & Invitation Round", "duration": "Variable (points dependent)"},
      {"stage": "Visa Application Lodgement to Decision", "duration": "3 - 8 months"}
    ]
  },
  "sales_playbook": {
    "target_client": "Skilled professionals, IT specialists, engineers, healthcare workers seeking permanent overseas relocation.",
    "pitch_points": [
      "Direct permanent residency without requiring state or employer sponsorship.",
      "Freedom to live, work, and study anywhere in the country.",
      "Pathway to citizenship with full social & healthcare benefits."
    ],
    "key_benefits": [
      "No regional lock-in",
      "Immediate permanent resident status",
      "Sponsor eligible family members"
    ]
  },
  "objections_rebuttals": [
    {
      "objection": "The points requirement is too competitive / high.",
      "rebuttal": "We strategically optimize your score through professional year, NAATI CCL language credentials, state nomination alternatives (190/491), and targeted English coaching to maximize every possible point."
    },
    {
      "objection": "Government fees and documentation costs seem expensive.",
      "rebuttal": "This is a one-time direct investment in permanent residency that gives lifelong work freedom, free healthcare, and subsidised education for children, typically recouped within your first 2-3 months of employment."
    }
  ],
  "faqs": [
    {
      "question": "Can I include my spouse and children in the application?",
      "answer": "Yes, your spouse and dependent children can be included at the time of application or added before the visa decision."
    },
    {
      "question": "Is a job offer required before applying?",
      "answer": "No job offer or employer sponsorship is required for independent skilled points visas."
    }
  ],
  "document_checklist_template": [
    {"category": "Identity", "document_name": "Valid Passport (Current & Previous)", "required_for": "all_applicants", "description": "Color scan of bio-data and travel stamp pages."},
    {"category": "Identity", "document_name": "National Identity Card / Aadhaar", "required_for": "all_applicants", "description": "National identity proof with photo and DOB."},
    {"category": "Education", "document_name": "Degree Certificates & Transcripts", "required_for": "primary_applicant", "description": "Consolidated marks sheets and degree convocation certificates."},
    {"category": "Work Experience", "document_name": "Reference Letters & Statement of Service", "required_for": "primary_applicant", "description": "Detailed roles and responsibilities on company letterhead."},
    {"category": "Work Experience", "document_name": "Pay Slips & Tax Returns (ITR / Form 16)", "required_for": "primary_applicant", "description": "Last 3-6 months pay slips and annual tax returns for each tenure."},
    {"category": "Language", "document_name": "English Test Scorecard (IELTS / PTE / TOEFL)", "required_for": "primary_applicant", "description": "Scorecard valid within 3 years of invitation."},
    {"category": "Character", "document_name": "Police Clearance Certificate (PCC)", "required_for": "applicants_16_plus", "description": "From every country lived in for 12+ months in past 10 years."}
  ],
  "info_sheet_sections": [
    {"section_key": "personal", "title": "Personal & Identity Details", "required": true},
    {"section_key": "contact_history", "title": "Contact & 10-Year Address History", "required": true},
    {"section_key": "education", "title": "Educational Qualifications", "required": true},
    {"section_key": "employment", "title": "Employment & Duties History", "required": true},
    {"section_key": "language", "title": "Language Test Scores", "required": true},
    {"section_key": "family", "title": "Family & Dependent Information", "required": true},
    {"section_key": "health_character", "title": "Health & Character Declarations", "required": true}
  ]
}
"""


def _clean_json_response(raw_text: str) -> str:
    """Clean markdown markers or surrounding conversational text from AI response."""
    text = raw_text.strip()
    # Remove markdown code block if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    # Extract first outer JSON object if embedded in text
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx : end_idx + 1]
    return text


async def research_product_with_ai(
    country: str,
    visa_name: str,
    category: str = "skilled_migration",
    visa_subclass: str = "",
    government_url: Optional[str] = None,
    migrate_page_url: Optional[str] = None,
    additional_context: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute live Perplexity research against official government sources and LEAMSS migrate pages.

    Returns structured Product Master dictionary ready for Admin review.
    """
    country_clean = country.strip()
    visa_clean = visa_name.strip()
    category_clean = category.strip()
    subclass_clean = visa_subclass.strip()

    prompt_parts = [
        f"Perform comprehensive official research to build a Product Master record for the following visa:",
        f"- Destination Country: {country_clean}",
        f"- Visa Name / Title: {visa_clean}",
        f"- Visa Category: {category_clean}",
    ]
    if subclass_clean:
        prompt_parts.append(f"- Visa Subclass / Stream Code: {subclass_clean}")
    if government_url:
        prompt_parts.append(f"- Official Government Source URL: {government_url.strip()}")
    if migrate_page_url:
        prompt_parts.append(f"- LEAMSS Migrate Reference URL: {migrate_page_url.strip()}")
    if additional_context:
        prompt_parts.append(f"- Admin Notes & Context: {additional_context.strip()}")

    prompt_parts.append(
        "\nConsult the official government immigration website for this country. "
        "Retrieve the exact current government visa application fees, minimum points criteria, mandatory requirements, "
        "published processing times, standard conditions, required documentation checklist, and common client questions. "
        "Return the complete JSON object matching the requested schema."
    )

    full_prompt = "\n".join(prompt_parts)

    try:
        raw_response, model_used = await call_perplexity(
            prompt=full_prompt,
            system_msg=SYSTEM_PROMPT,
            model="sonar-pro",
            max_tokens=4000,
            temperature=0.2,
            timeout=90.0,
        )

        cleaned_json = _clean_json_response(raw_response)
        parsed_data = json.loads(cleaned_json)

        # Ensure core fields are populated
        if not parsed_data.get("name"):
            parsed_data["name"] = f"{country_clean} {visa_clean}".strip()
        parsed_data["country"] = country_clean
        parsed_data["category"] = category_clean
        if subclass_clean and not parsed_data.get("visa_subclass"):
            parsed_data["visa_subclass"] = subclass_clean
        if government_url and government_url not in parsed_data.get("official_urls", []):
            parsed_data.setdefault("official_urls", []).append(government_url)
        if migrate_page_url and not parsed_data.get("migrate_page_url"):
            parsed_data["migrate_page_url"] = migrate_page_url

        parsed_data["_ai_generated"] = True
        parsed_data["_ai_model"] = model_used
        parsed_data["_researched_at"] = datetime.now(timezone.utc).isoformat()
        parsed_data["status"] = "draft"

        return parsed_data

    except json.JSONDecodeError as jde:
        logger.error("Failed to parse JSON from AI response: %s (raw text: %s)", jde, raw_response[:300])
        raise RuntimeError(f"AI returned invalid JSON format: {jde}")
    except Exception as e:
        logger.error("Product AI research failed: %s", e)
        raise RuntimeError(f"AI research failed: {str(e)}")
