"""Seed default agreement templates: Australia Standard, Australia Protection, Canada Express Entry.

Run via: python /app/backend/seed_agreement_templates.py
Idempotent — checks for existing template by (country, visa_category, policy_variant) before inserting.
"""
import asyncio
import uuid
import re
from datetime import datetime, timezone
from core.database import db

templates_col = db["agreement_templates"]


AUSTRALIA_STANDARD = """<h2>Service Agreement — LEAMSS Immigration Services (Australia)</h2>
<p><strong>Reference:</strong> {{pa_number}} &nbsp;|&nbsp; <strong>Date:</strong> {{agreement_date}}</p>

<p>This Agreement is entered into between <strong>Ladhani Education &amp; Migration Services Pvt Ltd</strong> (hereinafter "LEAMSS") and the Client named below for Australia immigration services.</p>

<h3>Client Details</h3>
<p>
<strong>Name:</strong> {{client_name}}<br/>
<strong>Date of Birth:</strong> {{client_dob}}<br/>
<strong>Address:</strong> {{client_address}}<br/>
<strong>Email:</strong> {{client_email}}<br/>
<strong>Phone:</strong> {{client_phone}}<br/>
<strong>Service:</strong> {{service_type}} ({{country}})
</p>

<h3>Annexure I — Application Procedure</h3>
<p><strong>Stage 1: Skill Assessment Filing</strong> — The applicant agrees to pay the relevant Skill Assessment Authority fees at lodgement. Clearing IELTS / PTE (Academic) / TOEFL with the prescribed score is solely the client's responsibility.</p>
<p><strong>Stage 2: Expression of Interest (EOI)</strong> — Upon receiving a positive Skill Assessment and clearing the required English bands, LEAMSS will lodge an online EOI. The application stays in the pool for up to 2 years awaiting an invitation from the Department of Home Affairs (DHA).</p>
<p><strong>Stage 3: Visa Application</strong> — Once the applicant receives the formal invitation, all required documents must be supplied to LEAMSS so the visa application can be lodged with DHA within 60 days (the invitation expires on the 60th day).</p>

<h3>Annexure II — Duties of LEAMSS</h3>
<p>LEAMSS shall:
• Assist in preparing the immigration case, attend telephone and email queries.
• Analyse current immigration law for the chosen visa category.
• Provide regular progress updates.
• Advise on documentation requirements.
• Lodge supporting submissions with the relevant Assessing Authority or Department.
• Advise of any changes to law or policy affecting the application.
• Communicate the outcome promptly and provide post-grant advice.</p>
<p>Preferred correspondence channel is email; queries will be answered within 48 hours. Advice provided during consultation is valid for 60 days. If documents are not provided within 90 days, the file will be closed. LEAMSS cannot guarantee government processing times or outcomes.</p>

<h3>Annexure III — Duties of the Applicant</h3>
<p>The Applicant shall:
• Provide all information truthfully in writing.
• Notify any change to address, education, training, status, job responsibilities, skills, marital status, or criminal charges.
• Establish proficiency in English by required IELTS / PTE / TEF bands.
• Respond promptly to LEAMSS' requests for documents.
• Refrain from contacting authorities directly while LEAMSS is engaged.
• Pay all fees in full before LEAMSS proceeds to the next stage.</p>
<p>Failing to pay the next instalment within <strong>10 days</strong> of receiving a positive Skill Assessment will close the application. Reopening will require a fee of <strong>Rs. 10,000 + GST</strong>.</p>

<h3>Annexure IV — Professional Fees &amp; Refund</h3>
<p>Total Professional Fee: <strong>INR {{proposal_final_amount}}</strong> (Payment Mode: {{payment_mode}}).</p>
<p><strong>Milestones:</strong>
• Milestone 1 (Registration): INR {{milestone_1_amount}} — due on {{milestone_1_date}}
• Milestone 2 (Positive Skill Assessment): INR {{milestone_2_amount}} — due on {{milestone_2_date}}
• Milestone 3 (Visa Lodgement): INR {{milestone_3_amount}} — due on {{milestone_3_date}}</p>
<p>An additional fee of <strong>Rs. 19,000 + GST</strong> applies at Stage 2 if the subclass is converted from 189 → 190 / 491. Disbursements (notary, courier, translation, police clearance, medicals, English test) are paid directly by the client.</p>
<p><strong>100% Refund of Professional Fees</strong> on negative Skill Assessment or Visa Refusal — except where there has been employer-verification negativity, false / misleading documents, voluntary withdrawal, medical / police-clearance rejection, or material change in law / personal circumstances.</p>

<h3>Annexure V — Migration Specialist Fee Payment</h3>
<p>Application fees payable to government authorities are subject to change and will be notified to the client. The application no. will not be shared until the outcome is received; fortnightly screen-shot updates will be provided. The agreement is valid for 1 year from signing; if filing has occurred within that year, services continue until the visa-office decision.</p>

<h3>Complaints &amp; Termination</h3>
<p>Complaints may be sent to <strong>{{leamss_agent_email}}</strong> and will be acknowledged within 4 days. Either party may end this agreement in writing; the client remains liable for any fees due. LEAMSS retains the right to keep a copy of the file for 2 years.</p>

<h3>Acceptance</h3>
<p>By paying the deposit and signing electronically below, the Client confirms acceptance of all terms above. This Agreement is legally binding in the country where the Client resides.</p>

<p><strong>Signed by Client:</strong> {{client_name}} &nbsp;|&nbsp; <strong>Date:</strong> {{agreement_date}}</p>
<p><strong>Signed by LEAMSS:</strong> {{agent_name}} &nbsp;|&nbsp; <strong>For:</strong> Ladhani Education &amp; Migration Services Pvt Ltd</p>"""


AUSTRALIA_PROTECTION = AUSTRALIA_STANDARD.replace(
    "<h3>Annexure V — Migration Specialist Fee Payment</h3>",
    """<h3>Annexure V — Protection Policy (Premium Variant) ⭐</h3>
<p>Under the LEAMSS Protection Policy, in addition to the Standard Refund clause, the Client is entitled to:
• <strong>100% Refund of Professional Fees</strong> if the visa is refused for any reason within LEAMSS' control;
• Free re-application support for one alternate pathway in the event of an unforeseen policy change affecting eligibility;
• Priority case handling with named senior consultant.</p>
<p>The Protection Policy fee is included in the Total Professional Fee above and is non-divisible.</p>

<h3>Annexure VI — Migration Specialist Fee Payment</h3>"""
).replace(
    "Service Agreement — LEAMSS Immigration Services (Australia)",
    "Service Agreement — LEAMSS Immigration Services (Australia · Protection Policy)"
)


CANADA_EXPRESS_ENTRY = """<h2>Retainer Agreement — LEAMSS Immigration Services (Canada · Express Entry)</h2>
<p><strong>Date of Agreement:</strong> {{agreement_date}} &nbsp;|&nbsp; <strong>Reference:</strong> {{pa_number}}</p>

<p>This Retainer Agreement is entered into between <strong>Ladhani Education &amp; Migration Services Pvt Ltd</strong> ("LEAMSS"), a member of the College of Immigration and Citizenship Consultants (CICC) — the regulator in Canada for immigration consultants — and the Client identified below.</p>

<h3>Client Details</h3>
<p>
<strong>Name:</strong> {{client_name}}<br/>
<strong>Date of Birth:</strong> {{client_dob}}<br/>
<strong>Address:</strong> {{client_address}}<br/>
<strong>Email:</strong> {{client_email}}<br/>
<strong>Phone:</strong> {{client_phone}}<br/>
<strong>Service:</strong> Canada Express Entry — Federal Skilled Worker Program (PR)
</p>

<h3>Service Validity</h3>
<p>LEAMSS' professional service is valid for <strong>1 (one) year</strong> from the date of execution. Once an Invitation To Apply (ITA) is received within this period, the service continues until the visa-office decision on the application.</p>

<h3>LEAMSS Responsibilities</h3>
<p>LEAMSS shall:
• File for Educational Credential Assessment (ECA) on the client's behalf
• Provide step-by-step guidance for IELTS / CELPIP / TEF / TCF tests
• File an Express Entry profile and maintain it during the validity period
• File any related Provincial Nominee Program (PNP) application upon notification of interest
• Provide complete representation till the final visa decision
• Maintain confidentiality of all client information per CICC code of ethics</p>

<h3>Client Responsibilities</h3>
<p>The Client shall:
• Provide all information and documents truthfully and in writing
• Notify changes in marital status, education, employment, address, criminal record
• Achieve required language proficiency (IELTS General / CELPIP / TEF / TCF) — solely the client's responsibility
• Provide the ECA fee, language test fee, biometric fee, and government PR fees directly
• Respond to LEAMSS requests within 7 days; failing this, the file may be closed</p>

<h3>Billing &amp; Milestones</h3>
<p>Total Professional Fee: <strong>INR {{proposal_final_amount}}</strong> (Payment Mode: {{payment_mode}}).</p>
<p>
• Milestone 1 — Registration: INR {{milestone_1_amount}} — due {{milestone_1_date}}
• Milestone 2 — On / before {{milestone_2_date}}: INR {{milestone_2_amount}}
• Milestone 3 — On Invitation To Apply (ITA): INR {{milestone_3_amount}} — due {{milestone_3_date}}
</p>

<h3>Refund Policy</h3>
<p>100% refund of professional fees if:
• ECA returns ineligible (and client did not misrepresent qualifications)
• Express Entry profile cannot be created due to point-deficit despite truthful info supplied at intake
</p>
<p>No refund where:
• Client withdraws voluntarily after profile is created
• Application is refused due to false / misleading documentation
• Refusal due to medicals / police clearance / criminality / character grounds
• Refusal due to a material change in IRCC policy after lodgement
</p>

<h3>Confidentiality, Force Majeure &amp; Dispute Resolution</h3>
<p>All client data is held in strict confidence per CICC norms. LEAMSS is not liable for delays caused by acts of God, government action, civil unrest, or pandemics. Any dispute shall be referred first to internal mediation; if unresolved, to the courts of Mumbai, India.</p>

<h3>Electronic Signature &amp; Binding Effect</h3>
<p>The Client agrees that an electronic signature carries the same legal weight as a wet-ink signature in line with the IT Act 2000 (India) and applicable international contract law. By signing electronically, the Client agrees to all terms above.</p>

<p><strong>Signed by Client:</strong> {{client_name}} &nbsp;|&nbsp; <strong>Date:</strong> {{agreement_date}}</p>
<p><strong>Signed by LEAMSS:</strong> {{agent_name}} &nbsp;|&nbsp; <strong>CICC RCIC Registered</strong></p>"""


def _detect(body):
    return sorted(set(re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", body)))


SEEDS = [
    {
        "name": "Australia · PR · Standard",
        "country": "Australia",
        "visa_category": "PR (Skilled Migration)",
        "policy_variant": "Standard",
        "body_html": AUSTRALIA_STANDARD,
        "is_active": True,
        "notes": "Default Australia Standard Skilled Migration agreement (subclasses 189/190/491).",
    },
    {
        "name": "Australia · PR · Protection Policy",
        "country": "Australia",
        "visa_category": "PR (Skilled Migration)",
        "policy_variant": "Protection",
        "body_html": AUSTRALIA_PROTECTION,
        "is_active": True,
        "notes": "Premium variant with 100% refund + free re-application for one alternate pathway.",
    },
    {
        "name": "Canada · PR · Express Entry",
        "country": "Canada",
        "visa_category": "PR (Express Entry)",
        "policy_variant": "Standard",
        "body_html": CANADA_EXPRESS_ENTRY,
        "is_active": True,
        "notes": "Federal Skilled Worker / Express Entry retainer agreement (CICC registered).",
    },
]


async def seed():
    upserted = 0
    for s in SEEDS:
        key = {"country": s["country"], "visa_category": s["visa_category"], "policy_variant": s["policy_variant"]}
        existing = await templates_col.find_one(key, {"_id": 0, "id": 1})
        if existing:
            print(f"⏭️  exists: {s['name']} (id {existing['id']}) — updating body")
            await templates_col.update_one(key, {"$set": {
                "body_html": s["body_html"],
                "placeholders": _detect(s["body_html"]),
                "updated_at": datetime.now(timezone.utc),
                "name": s["name"],
                "notes": s["notes"],
            }})
            continue
        rec = {
            "id": str(uuid.uuid4()),
            **s,
            "placeholders": _detect(s["body_html"]),
            "version": 1,
            "created_by": "system_seed",
            "created_by_name": "System Seed",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await templates_col.insert_one(rec)
        print(f"✅ inserted: {s['name']}")
        upserted += 1
    print(f"\nDone — {upserted} new, {len(SEEDS) - upserted} updated.")


if __name__ == "__main__":
    asyncio.run(seed())
