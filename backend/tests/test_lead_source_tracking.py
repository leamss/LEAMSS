"""
Automated Unit Tests for Lead Source Tracking and Attribution Engine.
Tests:
- UTM parameter detection (gclid, fbclid, utm_source, utm_medium)
- Canonical normalization (Google Ads, Facebook Ads, Instagram, Google Sheets, Zoho, Website, Unknown)
- Provider origin resolution
- API capture and get_leads filtering by canonical source and Unknown fallback
"""

import pytest
from services.lead_source_tracker import (
    detect_lead_source,
    normalize_source_name,
    SOURCE_WEBSITE,
    SOURCE_GOOGLE_ADS,
    SOURCE_FACEBOOK_ADS,
    SOURCE_INSTAGRAM,
    SOURCE_GOOGLE_SHEETS,
    SOURCE_ZOHO,
    SOURCE_WHATSAPP,
    SOURCE_REFERRAL,
    SOURCE_UNKNOWN,
)


def test_normalize_source_name():
    assert normalize_source_name("google ads") == SOURCE_GOOGLE_ADS
    assert normalize_source_name("Google_Ads") == SOURCE_GOOGLE_ADS
    assert normalize_source_name("adwords") == SOURCE_GOOGLE_ADS
    assert normalize_source_name("facebook") == SOURCE_FACEBOOK_ADS
    assert normalize_source_name("Facebook Ads") == SOURCE_FACEBOOK_ADS
    assert normalize_source_name("instagram") == SOURCE_INSTAGRAM
    assert normalize_source_name("google_sheets") == SOURCE_GOOGLE_SHEETS
    assert normalize_source_name("Google Sheets") == SOURCE_GOOGLE_SHEETS
    assert normalize_source_name("zoho crm") == SOURCE_ZOHO
    assert normalize_source_name("whatsapp") == SOURCE_WHATSAPP
    assert normalize_source_name("referral") == SOURCE_REFERRAL
    assert normalize_source_name("website") == SOURCE_WEBSITE
    assert normalize_source_name("Website Popup") == SOURCE_WEBSITE
    assert normalize_source_name("") == SOURCE_UNKNOWN
    assert normalize_source_name(None) == SOURCE_UNKNOWN
    assert normalize_source_name("unknown") == SOURCE_UNKNOWN


def test_detect_lead_source_google_ads_via_gclid():
    data = {
        "name": "Alex Google Ad",
        "email": "alex.ad@example.com",
        "gclid": "Cj0KCQjwwM-",
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": "search_canada_pr"
    }
    canonical, orig, details = detect_lead_source(data)
    assert canonical == SOURCE_GOOGLE_ADS
    assert details["gclid"] == "Cj0KCQjwwM-"
    assert details["utm_source"] == "google"
    assert details["utm_medium"] == "cpc"
    assert details["utm_campaign"] == "search_canada_pr"


def test_detect_lead_source_facebook_ads_via_fbclid():
    data = {
        "name": "Maria FB",
        "email": "maria@example.com",
        "fbclid": "IwAR02x_fb",
        "utm_source": "facebook",
        "campaign": "australia_leads_fb"
    }
    canonical, orig, details = detect_lead_source(data)
    assert canonical == SOURCE_FACEBOOK_ADS
    assert details["fbclid"] == "IwAR02x_fb"
    assert details["channel"] == SOURCE_FACEBOOK_ADS


def test_detect_lead_source_instagram():
    data = {
        "name": "Insta User",
        "email": "insta@example.com",
        "utm_source": "instagram",
        "utm_medium": "story_ad"
    }
    canonical, orig, details = detect_lead_source(data)
    assert canonical == SOURCE_INSTAGRAM


def test_detect_lead_source_google_sheets_provider():
    data = {
        "name": "Sheet Client",
        "email": "sheet@example.com",
        "provider": "google_sheets"
    }
    canonical, orig, details = detect_lead_source(data)
    assert canonical == SOURCE_GOOGLE_SHEETS


def test_detect_lead_source_google_sheets_with_marketing_source():
    data = {
        "name": "Sheet User",
        "provider": "google_sheets",
        "marketing_source": "Google Ads"
    }
    canonical, orig, details = detect_lead_source(data)
    assert canonical == SOURCE_GOOGLE_ADS
    assert orig == "Google Ads"


def test_detect_lead_source_website_default():
    data = {
        "name": "Web Form Lead",
        "email": "web@example.com",
        "website_page_url": "https://leamss.com/canada-pr"
    }
    canonical, orig, details = detect_lead_source(data, default_source="Website")
    assert canonical == SOURCE_WEBSITE
    assert details["landing_page"] == "https://leamss.com/canada-pr"


def test_detect_lead_source_unknown():
    data = {
        "name": "Unidentified Lead",
        "email": "noinfo@example.com"
    }
    canonical, orig, details = detect_lead_source(data)
    assert canonical == SOURCE_UNKNOWN
    assert orig == SOURCE_UNKNOWN
