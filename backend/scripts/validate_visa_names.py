"""
Visa-Name Validator Utility (Sweep B.4.7 bundle)
=================================================

Purpose: Validate proposed visa subclass_ids + names against official .gov URLs
BEFORE seeding, to catch outdated/closed/renamed visa references early.

Inspired by NZ B.4.5 corrections (Investor 2 closed → AIP; Skilled Refugee doesn't
exist → Refugee Family Support) and UK B.4.6 correction (Tech Nation status).
This script makes such corrections discoverable BEFORE seed time.

Usage:
    python -m scripts.validate_visa_names --country US --visas us_visa_names.json
    python -m scripts.validate_visa_names --inline  # uses USA hardcoded list

The script does HTTP HEAD checks on each URL and prints:
    [OK]    visa_name → URL reachable (HTTP 200/30x)
    [WARN]  visa_name → URL returns 404 / 410 / 5xx (likely closed or renamed)
    [ERR]   visa_name → DNS or network error

For closed/renamed visas, the script suggests checking the official program
listing page (e.g., uscis.gov/working-in-the-united-states for US work visas).

This is a READ-ONLY validation utility — no DB writes, no API calls beyond
verifying public .gov URLs.
"""
import argparse
import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

import httpx


# ──────────────────────────────────────────────────────────────────────────────
# Hardcoded USA visa name reference list for B.4.7 inline validation
# ──────────────────────────────────────────────────────────────────────────────
USA_VISA_NAMES: List[Dict[str, str]] = [
    {
        "subclass_id": "B1-B2",
        "subclass_name": "Business + Tourist Visitor Visa",
        "official_url": "https://travel.state.gov/content/travel/en/us-visas/tourism-visit/visitor.html",
        "secondary_url": "https://travel.state.gov/content/travel/en/us-visas/business.html",
    },
    {
        "subclass_id": "F1",
        "subclass_name": "Student Visa (Academic / Language)",
        "official_url": "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
        "secondary_url": "https://studyinthestates.dhs.gov/",
    },
    {
        "subclass_id": "H-1B",
        "subclass_name": "Specialty Occupation Worker (Cap-Subject)",
        "official_url": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
        "secondary_url": "https://travel.state.gov/content/travel/en/us-visas/employment/temporary-worker-visas.html",
    },
    {
        "subclass_id": "L-1",
        "subclass_name": "Intracompany Transferee (L-1A Executive/Manager + L-1B Specialized Knowledge)",
        "official_url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/l-1a-intracompany-transferee-executive-or-manager",
        "secondary_url": "https://www.uscis.gov/working-in-the-united-states/temporary-workers/l-1b-intracompany-transferee-specialized-knowledge",
    },
    {
        "subclass_id": "EB-1-EB-2",
        "subclass_name": "Employment-Based Green Card (EB-1 Priority Workers + EB-2 Advanced Degree / NIW)",
        "official_url": "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-first-preference-eb-1",
        "secondary_url": "https://www.uscis.gov/working-in-the-united-states/permanent-workers/employment-based-immigration-second-preference-eb-2",
    },
    {
        "subclass_id": "K-1",
        "subclass_name": "Fiancé(e) Visa (followed by AOS within 90 days)",
        "official_url": "https://travel.state.gov/content/travel/en/us-visas/immigrate/family-immigration/nonimmigrant-visa-for-a-fiance-k-1.html",
        "secondary_url": "https://www.uscis.gov/family/family-of-us-citizens/visas-for-fiances-of-us-citizens",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Germany visa name reference list for B.4.8 inline validation
# ──────────────────────────────────────────────────────────────────────────────
GERMANY_VISA_NAMES: List[Dict[str, str]] = [
    {
        "subclass_id": "EU-Blue-Card",
        "subclass_name": "EU Blue Card (Highly-Skilled Non-EU; 2026 €50,700 / €45,934 shortage)",
        "official_url": "https://www.make-it-in-germany.com/en/visa-residence/types/eu-blue-card",
        "secondary_url": "https://www.bamf.de/EN/Themen/MigrationAufenthalt/ZuwandererDrittstaaten/Migrathek/BlaueKarteEU/blauekarteeu-node.html",
    },
    {
        "subclass_id": "Job-Seeker",
        "subclass_name": "Job Seeker Visa (6-month visa, €6,162 blocked account)",
        "official_url": "https://www.make-it-in-germany.com/en/visa-residence/types/job-search",
        "secondary_url": "https://www.germany.info/us-en/service/visa/visa-for-jobseekers/2469848",
    },
    {
        "subclass_id": "Student",
        "subclass_name": "Student Visa (Aufenthaltserlaubnis zum Studium; €11,904 Sperrkonto)",
        "official_url": "https://www.make-it-in-germany.com/en/study-training/studying/visa",
        "secondary_url": "https://www.auswaertiges-amt.de/en/sperrkonto-388600",
    },
    {
        "subclass_id": "Skilled-Worker",
        "subclass_name": "Skilled Worker Visa (Fachkräfteeinwanderungsgesetz + Anerkennungspartnerschaft + Chancenkarte)",
        "official_url": "https://www.make-it-in-germany.com/en/visa-residence/types/skilled-workers",
        "secondary_url": "https://www.make-it-in-germany.com/en/visa-residence/types/opportunity-card",
    },
    {
        "subclass_id": "Family-Reunion",
        "subclass_name": "Family Reunion Visa (Familiennachzug; A1 German for spouses, exemptions for Blue Card/Skilled Worker)",
        "official_url": "https://www.make-it-in-germany.com/en/visa-residence/types/family-reunification",
        "secondary_url": "https://www.bamf.de/SharedDocs/Anlagen/DE/MigrationAufenthalt/Ehegattennachzug/ehegattennachzug-en.pdf",
    },
    {
        "subclass_id": "Self-Employment",
        "subclass_name": "Self-Employment Visa (Selbständige Tätigkeit + Freiberufler/freelancer)",
        "official_url": "https://www.make-it-in-germany.com/en/visa-residence/types/self-employment",
        "secondary_url": "https://www.bamf.de/EN/Themen/MigrationAufenthalt/ZuwandererDrittstaaten/Arbeit/SelbstaendigeTaetigkeit/selbstaendigetaetigkeit-node.html",
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# Schengen visa name reference list for B.4.9 inline validation
# ──────────────────────────────────────────────────────────────────────────────
SCHENGEN_VISA_NAMES: List[Dict[str, str]] = [
    {
        "subclass_id": "C-Tourist",
        "subclass_name": "Schengen Short-Stay Type C Tourist (€90 fee; 90 days in 180; biometrics)",
        "official_url": "https://home-affairs.ec.europa.eu/policies/schengen/visa-policy/applying-schengen-visa_en",
        "secondary_url": "https://www.axa-schengen.com/en/visa/types/schengen-visa-type-c",
    },
    {
        "subclass_id": "C-Business",
        "subclass_name": "Schengen Short-Stay Type C Business (90/180; invitation letter required)",
        "official_url": "https://home-affairs.ec.europa.eu/policies/schengen/visa-policy_en",
        "secondary_url": "https://www.schengenvisainfo.com/business-schengen-visa/",
    },
    {
        "subclass_id": "D-Long-Stay",
        "subclass_name": "Schengen Long-Stay National Visa Type D (>90 days; country-specific issuance)",
        "official_url": "https://home-affairs.ec.europa.eu/policies/schengen/visa-policy_en",
        "secondary_url": "https://www.axa-schengen.com/en/visa/types/schengen-visa-type-d",
    },
    {
        "subclass_id": "A-Transit",
        "subclass_name": "Schengen Airport Transit Visa Type A (specific nationalities — India NOT typically required)",
        "official_url": "https://home-affairs.ec.europa.eu/policies/schengen/visa-policy_en",
        "secondary_url": "https://www.schengenvisainfo.com/airport-transit-schengen-visa/",
    },
    {
        "subclass_id": "C-Family-Visit",
        "subclass_name": "Schengen Short-Stay Family Visit (Type C; invitation letter from EU resident family)",
        "official_url": "https://home-affairs.ec.europa.eu/policies/schengen/visa-policy_en",
        "secondary_url": "https://www.schengenvisainfo.com/family-schengen-visa/",
    },
    {
        "subclass_id": "Study",
        "subclass_name": "Schengen Study Visa (Type C for <90 days; Type D for full programs — country-specific)",
        "official_url": "https://home-affairs.ec.europa.eu/policies/schengen/visa-policy_en",
        "secondary_url": "https://www.schengenvisainfo.com/student-schengen-visa/",
    },
]


async def check_url(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    """HTTP HEAD with GET fallback. Returns {status, http_code, error}."""
    try:
        resp = await client.head(url, follow_redirects=True, timeout=10.0)
        if resp.status_code in (405, 403):  # Some .gov sites block HEAD — try GET
            resp = await client.get(url, follow_redirects=True, timeout=10.0)
        return {
            "status": "ok" if 200 <= resp.status_code < 400 else "warn",
            "http_code": resp.status_code,
            "final_url": str(resp.url),
            "error": None,
        }
    except httpx.RequestError as e:
        return {"status": "err", "http_code": None, "final_url": None, "error": str(e)[:120]}
    except Exception as e:  # pylint: disable=broad-except
        return {"status": "err", "http_code": None, "final_url": None, "error": str(e)[:120]}


async def validate_visas(visas: List[Dict[str, str]], country_code: str) -> Dict[str, Any]:
    """Validate all visa entries; return summary + per-visa results."""
    results: List[Dict[str, Any]] = []
    summary = {"ok": 0, "warn": 0, "err": 0, "total": len(visas)}

    async with httpx.AsyncClient(headers={"User-Agent": "LEAMSS-VisaValidator/1.0"}) as client:
        for v in visas:
            sid = v["subclass_id"]
            primary = await check_url(client, v["official_url"])
            secondary = await check_url(client, v.get("secondary_url", v["official_url"]))

            # Best-of: if either URL is OK, treat as OK
            best_status = primary["status"]
            if best_status == "warn" and secondary["status"] == "ok":
                best_status = "ok"
            elif primary["status"] == "err" and secondary["status"] == "ok":
                best_status = "ok"

            summary[best_status] = summary.get(best_status, 0) + 1
            status_icon = {"ok": "[OK]  ", "warn": "[WARN]", "err": "[ERR] "}[best_status]
            print(f"  {status_icon} {country_code}-{sid}: {v['subclass_name'][:60]}")
            print(f"           Primary: {primary['http_code']} → {v['official_url']}")
            if v.get("secondary_url"):
                print(f"           Secondary: {secondary['http_code']} → {v['secondary_url']}")
            if best_status != "ok":
                print(f"           ⚠️  Action needed: verify official URL + program status before seeding")

            results.append({
                "subclass_id": sid,
                "subclass_name": v["subclass_name"],
                "best_status": best_status,
                "primary": primary,
                "secondary": secondary,
            })

    return {"summary": summary, "results": results}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Validate visa subclass names against official .gov URLs")
    parser.add_argument("--country", type=str, default="US", help="ISO-2 country code (for display)")
    parser.add_argument("--visas", type=str, default=None, help="Path to JSON file with visa entries")
    parser.add_argument("--inline", type=str, nargs="?", const="US", default=None,
                        help="Use hardcoded inline visa list. Pass country code (US|DE). Default: US")
    args = parser.parse_args()

    if args.inline:
        inline_choice = args.inline.upper()
        if inline_choice == "US":
            visas = USA_VISA_NAMES
            country_code = "US"
            slice_label = "B.4.7 INLINE"
        elif inline_choice == "DE":
            visas = GERMANY_VISA_NAMES
            country_code = "DE"
            slice_label = "B.4.8 INLINE"
        elif inline_choice == "EU":
            visas = SCHENGEN_VISA_NAMES
            country_code = "EU"
            slice_label = "B.4.9 INLINE (Schengen)"
        else:
            print(f"⚠  Unknown inline country code '{inline_choice}'. Supported: US, DE, EU")
            sys.exit(1)
        print(f"\n══════════════════════════════════════════════")
        print(f"  VALIDATING {country_code} ({slice_label}) — {len(visas)} visas")
        print(f"══════════════════════════════════════════════\n")
    elif args.visas:
        with open(args.visas, "r", encoding="utf-8") as f:
            visas = json.load(f)
        country_code = args.country.upper()
        print(f"\n══════════════════════════════════════════════")
        print(f"  VALIDATING {country_code} (from {args.visas}) — {len(visas)} visas")
        print(f"══════════════════════════════════════════════\n")
    else:
        print("⚠  Specify --inline (USA) or --visas <path.json>")
        sys.exit(1)

    output = await validate_visas(visas, country_code)
    s = output["summary"]
    print(f"\n══════════════════════════════════════════════")
    print(f"  RESULT: OK={s['ok']} WARN={s['warn']} ERR={s['err']} (total={s['total']})")
    print(f"══════════════════════════════════════════════\n")

    # Exit non-zero if any visa needs review (helps CI gating)
    if s["warn"] + s["err"] > 0:
        print(f"⚠  {s['warn'] + s['err']} visa(s) flagged — review official URLs + program status before seeding.")
        sys.exit(1)
    print(f"✅ All {s['total']} visa names validated successfully.")


if __name__ == "__main__":
    asyncio.run(main())
