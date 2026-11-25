"""
Lead Source Tracking and Normalization Service.
Accurately identifies, normalizes, and enriches lead sources across:
- Website (Forms, Popups, Landing Pages, Public Atlas, Organic Web)
- Google Ads (gclid, wbraid, gbraid, utm_source=google, utm_medium=cpc)
- Facebook Ads (Meta Lead Ads webhook, fbclid, utm_source=facebook)
- Instagram (Instagram Lead Ads webhook, utm_source=instagram)
- Google Sheets (Connected Spreadsheets sync & webhooks)
- Zoho (Zoho CRM / Zoho Forms webhook or pull sync)
- WhatsApp (Direct click-to-chat / WhatsApp leads)
- Referral (Partner, agent, or client referrals)
- Direct Call / Walk-In
- Unknown (When source cannot be identified or is missing)
"""

from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone

# Canonical Source Constants
SOURCE_WEBSITE = "Website"
SOURCE_GOOGLE_ADS = "Google Ads"
SOURCE_FACEBOOK_ADS = "Facebook Ads"
SOURCE_INSTAGRAM = "Instagram"
SOURCE_GOOGLE_SHEETS = "Google Sheets"
SOURCE_ZOHO = "Zoho"
SOURCE_WHATSAPP = "WhatsApp"
SOURCE_REFERRAL = "Referral"
SOURCE_DIRECT_CALL = "Direct Call"
SOURCE_WALK_IN = "Walk-In"
SOURCE_SAMPLE_LEADS = "Sample Leads"
SOURCE_EXCEL_IMPORT = "Excel Import"
SOURCE_CALENDLY = "Calendly"
SOURCE_UNKNOWN = "Unknown"

ALL_CANONICAL_SOURCES = [
    SOURCE_WEBSITE,
    SOURCE_GOOGLE_ADS,
    SOURCE_FACEBOOK_ADS,
    SOURCE_INSTAGRAM,
    SOURCE_GOOGLE_SHEETS,
    SOURCE_ZOHO,
    SOURCE_WHATSAPP,
    SOURCE_REFERRAL,
    SOURCE_DIRECT_CALL,
    SOURCE_WALK_IN,
    SOURCE_EXCEL_IMPORT,
    SOURCE_CALENDLY,
    SOURCE_SAMPLE_LEADS,
    SOURCE_UNKNOWN,
]


def normalize_source_name(raw_source: Optional[str]) -> str:
    """Normalizes an existing or raw source string to its canonical source name."""
    if not raw_source:
        return SOURCE_UNKNOWN
    s = str(raw_source).strip()
    if not s or s.lower() in ["", "none", "null", "undefined", "unknown", "n/a", "?"]:
        return SOURCE_UNKNOWN

    lower = s.lower()

    # Google Ads
    if any(k in lower for k in ["google ads", "google_ads", "googleads", "adwords", "google cpc", "google paid"]):
        return SOURCE_GOOGLE_ADS

    # Facebook Ads
    if any(k in lower for k in ["facebook ads", "facebook_ads", "facebook", "fb ads", "meta ads", "meta lead"]):
        return SOURCE_FACEBOOK_ADS

    # Instagram
    if any(k in lower for k in ["instagram ads", "instagram_ads", "instagram", "ig ads", "insta"]):
        return SOURCE_INSTAGRAM

    # Google Sheets
    if any(k in lower for k in ["google sheets", "google_sheets", "googlesheets", "spreadsheet", "sheet lead"]):
        return SOURCE_GOOGLE_SHEETS

    # Zoho
    if any(k in lower for k in ["zoho", "zoho crm", "zoho_crm", "zoho forms"]):
        return SOURCE_ZOHO

    # WhatsApp
    if any(k in lower for k in ["whatsapp", "wa_click", "wa_inquiry"]):
        return SOURCE_WHATSAPP

    # Referral
    if any(k in lower for k in ["referral", "referee", "partner", "agent", "word of mouth"]):
        return SOURCE_REFERRAL

    # Walk-in / Direct Call
    if any(k in lower for k in ["walk in", "walk-in", "walkin", "branch"]):
        return SOURCE_WALK_IN
    if any(k in lower for k in ["direct call", "phone call", "incoming call", "telephony"]):
        return SOURCE_DIRECT_CALL

    # Excel / Bulk import
    if any(k in lower for k in ["excel", "csv", "bulk import", "file import"]):
        return SOURCE_EXCEL_IMPORT

    # Calendly
    if any(k in lower for k in ["calendly", "calendly booking", "calendly_booking", "calendly_meeting"]):
        return SOURCE_CALENDLY

    # Sample
    if "sample" in lower:
        return SOURCE_SAMPLE_LEADS

    # Website (forms, popups, landing pages, organic web)
    if any(k in lower for k in ["website", "web", "popup", "general enquiry", "atlas", "landing page", "organic", "portal"]):
        return SOURCE_WEBSITE

    # If unrecognized non-empty string, preserve title-cased or map to Unknown if generic
    return s.title() if len(s) > 2 else SOURCE_UNKNOWN


def detect_lead_source(data: Dict[str, Any], default_source: Optional[str] = None) -> Tuple[str, str, Dict[str, Any]]:
    """
    Analyzes incoming payload, query params, UTM parameters, ad click IDs, and explicit source fields.
    Returns:
        (canonical_source, original_source, source_details)
    """
    raw_source = str(data.get("source") or data.get("lead_source") or "").strip()
    raw_provider = str(data.get("provider") or "").strip().lower()

    # Extract UTMs and ad identifiers
    utm_source = str(data.get("utm_source") or "").strip()
    utm_medium = str(data.get("utm_medium") or "").strip()
    utm_campaign = str(data.get("utm_campaign") or data.get("campaign") or "").strip()
    utm_term = str(data.get("utm_term") or "").strip()
    utm_content = str(data.get("utm_content") or "").strip()
    gclid = str(data.get("gclid") or data.get("wbraid") or data.get("gbraid") or "").strip()
    fbclid = str(data.get("fbclid") or "").strip()
    referrer = str(data.get("referrer") or data.get("referrer_url") or "").strip()
    landing_page = str(data.get("website_page_url") or data.get("page_url") or data.get("landing_page") or "").strip()
    page_title = str(data.get("website_page_title") or data.get("page_title") or "").strip()
    marketing_source = str(data.get("marketing_source") or "").strip()

    # Determine original source record
    original_source = raw_source or marketing_source or raw_provider
    if not original_source:
        if utm_source:
            original_source = f"utm:{utm_source}"
        elif gclid:
            original_source = "Google Click (gclid)"
        elif fbclid:
            original_source = "Facebook Click (fbclid)"
        elif default_source:
            original_source = default_source
        else:
            original_source = SOURCE_UNKNOWN

    canonical_source: str = SOURCE_UNKNOWN

    # 1. Check Ad Click Identifiers & UTM parameters (Highest Attribution Priority)
    lower_utm_src = utm_source.lower()
    lower_utm_med = utm_medium.lower()

    if gclid or "google" in lower_utm_src or lower_utm_med in ["cpc", "ppc", "adwords"]:
        if "google" in lower_utm_src or gclid or lower_utm_med in ["cpc", "ppc", "adwords"]:
            canonical_source = SOURCE_GOOGLE_ADS

    elif fbclid or any(k in lower_utm_src for k in ["facebook", "fb", "meta"]):
        canonical_source = SOURCE_FACEBOOK_ADS

    elif any(k in lower_utm_src for k in ["instagram", "ig"]):
        canonical_source = SOURCE_INSTAGRAM

    # 2. Check provider / platform integration origin
    elif raw_provider:
        if raw_provider in ["google_sheets", "googlesheets", "sheets", "spreadsheet"]:
            # If Google Sheets row has a specific marketing source (e.g. "Google Ads"), normalize it
            if marketing_source:
                norm_mkt = normalize_source_name(marketing_source)
                canonical_source = norm_mkt if norm_mkt != SOURCE_UNKNOWN else SOURCE_GOOGLE_SHEETS
            else:
                canonical_source = SOURCE_GOOGLE_SHEETS
        elif raw_provider in ["facebook", "facebook_ads", "meta"]:
            canonical_source = SOURCE_FACEBOOK_ADS
        elif raw_provider in ["instagram", "instagram_ads"]:
            canonical_source = SOURCE_INSTAGRAM
        elif raw_provider in ["zoho", "zoho_crm"]:
            canonical_source = SOURCE_ZOHO
        elif raw_provider in ["calendly", "calendly_booking", "calendly_meeting"]:
            canonical_source = SOURCE_CALENDLY
        else:
            canonical_source = normalize_source_name(raw_provider)

    # 3. Check explicit raw_source or marketing_source
    elif raw_source or marketing_source:
        source_to_test = raw_source if raw_source and raw_source.lower() not in ["website", "direct entry"] else (marketing_source or raw_source)
        canonical_source = normalize_source_name(source_to_test)

    # 4. Fallback to default_source if provided
    elif default_source:
        canonical_source = normalize_source_name(default_source)

    # 5. Fallback to Unknown if could not be determined
    else:
        canonical_source = SOURCE_UNKNOWN

    # Ensure canonical_source is never empty or None
    if not canonical_source or canonical_source == "":
        canonical_source = SOURCE_UNKNOWN

    source_details = {
        "channel": canonical_source,
        "original_source": original_source,
        "utm_source": utm_source or None,
        "utm_medium": utm_medium or None,
        "utm_campaign": utm_campaign or None,
        "utm_term": utm_term or None,
        "utm_content": utm_content or None,
        "gclid": gclid or None,
        "fbclid": fbclid or None,
        "referrer": referrer or None,
        "landing_page": landing_page or None,
        "page_title": page_title or None,
        "captured_at": datetime.now(timezone.utc).isoformat()
    }

    return canonical_source, original_source, source_details
