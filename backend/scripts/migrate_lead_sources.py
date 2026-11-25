"""
One-time Migration / Backfill Script:
Normalizes existing CRM lead sources into canonical sources:
- 'Website', 'Google Ads', 'Facebook Ads', 'Instagram', 'Google Sheets', 'Zoho', 'WhatsApp', 'Referral', 'Walk-In', 'Direct Call', 'Unknown'
- Preserves raw source in 'original_source'.
- Sets 'source_details' structure.
"""

import asyncio
from datetime import datetime, timezone
import sys
import os

# Ensure backend root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db
from services.lead_source_tracker import normalize_source_name, SOURCE_UNKNOWN, SOURCE_WEBSITE


async def migrate_sources():
    print("Starting Lead Sources Normalization Migration...")
    leads_col = db["leads"]
    total = await leads_col.count_documents({})
    print(f"Total leads in database: {total}")

    cursor = leads_col.find({})
    updated_count = 0

    async for lead in cursor:
        lead_id = lead["id"]
        raw_source = lead.get("source")
        existing_orig = lead.get("original_source")
        orig_source = existing_orig or raw_source or SOURCE_UNKNOWN

        # Check UTMs and click IDs
        utm_src = (lead.get("utm_source") or "").lower()
        gclid = lead.get("gclid")
        fbclid = lead.get("fbclid")

        if gclid or "google" in utm_src or (lead.get("utm_medium") or "").lower() in ["cpc", "ppc"]:
            canonical = "Google Ads"
        elif fbclid or "facebook" in utm_src or "fb" in utm_src:
            canonical = "Facebook Ads"
        elif "instagram" in utm_src or "ig" in utm_src:
            canonical = "Instagram"
        else:
            canonical = normalize_source_name(raw_source)

        # Fallback to Website if tag includes website/popup/atlas
        tags = lead.get("tags") or []
        if canonical == SOURCE_UNKNOWN:
            if any(t in tags for t in ["website", "popup_enquiry", "general_enquiry", "public_atlas"]):
                canonical = SOURCE_WEBSITE

        source_details = lead.get("source_details") or {
            "channel": canonical,
            "original_source": orig_source,
            "utm_source": lead.get("utm_source"),
            "utm_medium": lead.get("utm_medium"),
            "utm_campaign": lead.get("utm_campaign") or lead.get("campaign"),
            "gclid": gclid,
            "fbclid": fbclid,
            "landing_page": lead.get("website_page_url"),
            "captured_at": (lead.get("created_at") if isinstance(lead.get("created_at"), str) else datetime.now(timezone.utc).isoformat())
        }

        update_fields = {
            "source": canonical,
            "original_source": orig_source,
            "source_details": source_details
        }

        if raw_source == "Website Popup":
            update_fields["subsource"] = "Website Popup"

        await leads_col.update_one(
            {"id": lead_id},
            {"$set": update_fields}
        )
        updated_count += 1

    print(f"Migration completed! Updated {updated_count} leads.")

    # Print summary of sources now in DB
    distinct_sources = await leads_col.distinct("source")
    print("New distinct canonical sources in DB:", distinct_sources)
    for s in distinct_sources:
        cnt = await leads_col.count_documents({"source": s})
        print(f"  - {s}: {cnt}")


if __name__ == "__main__":
    asyncio.run(migrate_sources())
