"""Phase 20.3 — Initial Pre-Assessment Fee Policies seed.

6 policies based on Sir's brochure-derived defaults:
  - AU/PR · CA/PR · NZ/PR: ₹5,100 (current standard)
  - GLOBAL/ANY: ₹5,100 (catch-all final fallback)
  - AU/STUDY: ₹3,000 (cheaper PA for student visa pathway)
  - CA/WORK: ₹4,500 (work-permit specific)
"""

SEED_POLICIES = [
    {
        "country_code": "AU", "visa_category": "PR",
        "fee_inr": 5100,
        "policy_name": "AU PR Standard 2026",
        "rationale": "Standard pre-assessment fee for Australia PR (189/190/491) offshore applicants. Covers initial occupation + eligibility evaluation.",
    },
    {
        "country_code": "CA", "visa_category": "PR",
        "fee_inr": 5100,
        "policy_name": "CA PR Express Entry Standard 2026",
        "rationale": "Standard pre-assessment fee for Canada PR (Express Entry / PNP) applicants.",
    },
    {
        "country_code": "NZ", "visa_category": "PR",
        "fee_inr": 5100,
        "policy_name": "NZ PR Skilled Migrant Standard 2026",
        "rationale": "Standard pre-assessment fee for New Zealand Skilled Migrant Category.",
    },
    {
        "country_code": "GLOBAL", "visa_category": "ANY",
        "fee_inr": 5100,
        "policy_name": "Global Fallback Standard 2026",
        "rationale": "Catch-all fallback policy when no specific country/visa policy matches. Ensures resolver always returns a valid amount.",
    },
    {
        "country_code": "AU", "visa_category": "STUDY",
        "fee_inr": 3000,
        "policy_name": "AU Student Visa PA 2026",
        "rationale": "Lower pre-assessment fee for student visa pathway (sub-class 500). Reduced scope as student visa eligibility is more straightforward than PR.",
    },
    {
        "country_code": "CA", "visa_category": "WORK",
        "fee_inr": 4500,
        "policy_name": "CA Work Permit PA 2026",
        "rationale": "Slightly reduced pre-assessment fee for Canada work-permit (LMIA + LMIA-exempt) pathways.",
    },
]
