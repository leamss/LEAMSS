"""Seed default agreement templates — verbatim text from user-provided LEAMSS DOCX files.
Australia Standard, Australia Protection, Canada Express Entry.

Run: python /app/backend/seed_agreement_templates.py
"""
import asyncio
import uuid
import re
from datetime import datetime, timezone
from core.database import db

templates_col = db["agreement_templates"]


# =============================================================
# AUSTRALIA STANDARD — verbatim from user's DOCX
# =============================================================
AUSTRALIA_STANDARD = """<div class="agreement-doc">

<h1 class="title">Service Agreement — LEAMSS Immigration Services (Australia)</h1>
<p class="meta"><strong>Reference:</strong> {{pa_number}} &nbsp;&nbsp;|&nbsp;&nbsp; <strong>Date:</strong> {{agreement_date}}</p>

<p>This Agreement is entered into between <strong>Ladhani Education &amp; Migration Services Pvt Ltd</strong> (hereinafter "LEAMSS") and the Client named below for Australia immigration services.</p>

<h2>Client Details</h2>
<table class="client-details">
<tr><td><strong>Name (As per Passport)</strong></td><td>{{client_name}}</td></tr>
<tr><td><strong>Date of Birth</strong></td><td>{{client_dob}}</td></tr>
<tr><td><strong>Address (Current and/or as per Passport)</strong></td><td>{{client_address}}</td></tr>
<tr><td><strong>Email ID (Active and Valid)</strong></td><td>{{client_email}}</td></tr>
<tr><td><strong>Phone Number</strong></td><td>{{client_phone}}</td></tr>
<tr><td><strong>Service</strong></td><td>{{service_type}} ({{country}})</td></tr>
</table>

<p class="annex-list"><strong>The Annexures agreed to are:</strong><br/>
Annexure I: Application procedure<br/>
Annexure II: Duties of LEAMSS<br/>
Annexure III: Duties of the Applicant and Terms and Conditions<br/>
Annexure IV: Professional Fees &amp; Refund Clause<br/>
Annexure V: Migration Specialist Fee Payment</p>

<h2>Annexure I: Application Procedure</h2>

<h3>Stage 1: Filing for Skill Assessment</h3>
<p>Filing for skill assessment to the relevant skill assessment authorities. The applicant agrees to pay the Skill Assessment Authority fees at the time of lodging the application for skill assessment. Clearing the IELTS or PTE (Academic) or TOEFL Test with appropriate score as advised is solely the client's responsibility.</p>
<p><em>* Application cannot proceed to Stage 2 unless the applicant has received positive skills assessment and minimum required English score. (For some Skill Assessments, it is mandatory to clear English Test at Stage 1.)</em></p>

<h3>Stage 2: Filing for EOI (Expression of Interest)</h3>
<p>w.e.f. 1st July 2012 (Rules implemented on 1st July 2012). After receiving positive Skills Assessment and clearing the required IELTS band(s) along with all other information (to be provided by the applicant), LEAMSS.COM will file an online Expression of Interest (EOI). The application will stay in the pool created for the purpose by DHA (Department of Home Affairs) for up to 2 years.</p>
<p>The applicant will then wait for an invitation from the Department of Home Affairs to make a visa application. The invite may come in during a time frame lasting up to 2 years and is determined by various factors — including but not limited to the skills and qualifications needed in the Australian labor market, and/or the selection of the profile from the EOI pool by an Australian employer, region, or state.</p>

<h3>Stage 3: Getting Invitation and Filing with DHA within 60 days</h3>
<p>If and once the applicant gets the invite, they must provide all documents to the immigration specialist so as to enable LEAMSS to lodge the visa application with DHA within 60 days of receipt of the formal invite.</p>
<p><em>* It is advised to file with Department of Home Affairs within 60 days as the invitation expires on the 60th day.</em></p>

<h2>Annexure II: Duties of Ladhani Education &amp; Migration Services (LEAMSS)</h2>
<p><strong>LEAMSS Services and Obligations:</strong></p>
<ul>
<li>Assist the client in preparation of his/her immigration case, telephone and email attendances.</li>
<li>Analyze current immigration law relating to the visa category.</li>
<li>Regular client updates on development and progress of the application.</li>
<li>Provide advice and assistance relating to documentation required to support the application.</li>
<li>Prepare and lodge supporting submissions to the relevant Assessing Authority or Department.</li>
<li>Wherever possible, supply any further documentation or information requested by the Department on receipt of documents from you.</li>
<li>During the processing of the application, advise you of any changes to the law or Department policy requirements affecting the visa application.</li>
<li>Advise you promptly of the outcome of the application.</li>
<li>Provide post-grant migration advice regarding visa conditions and requirements.</li>
</ul>

<p>Our preferred method of correspondence is via email. We aim to answer all queries within <strong>48 hours</strong>. Direct contact details for your agent will be provided upon commencement of our service.</p>
<p>After we have given you all the information and advice we can during our consultation process, you must pay your fees in full. If you need help to prepare your file before you hand it in, we are happy to help you under the following conditions — and we will not charge you extra for this:</p>
<ul>
<li>We will help you prepare and hand in your file.</li>
<li>We cannot be held responsible for the quality of the documents you provide.</li>
</ul>
<p>Because immigration laws and policies are continually being updated and amended, the advice we provide during our consultation process can only be used for <strong>60 days</strong>. We cannot be held legally responsible for any immigration policy or laws that change and that may greatly affect your case. If you do not give us the documents we need within <strong>90 days</strong> of your consultation, we will have to close your file. Your case cannot stay open forever, as immigration laws and policies are constantly changing.</p>
<p>We have no control over the time it takes to process your application once we have sent it to the governing organization. We are also not able to guarantee their final decision on your case. We cannot accept legal responsibility if your application is greatly affected by a change in the law or a policy.</p>

<h2>Annexure III: Duties of the Applicant and Terms and Conditions</h2>
<p><strong>Working together with LEAMSS — the Client agrees to:</strong></p>
<ul>
<li>Provide all information truthfully in writing requested by the company and the processing visa office as per company's instructions. The client shall be responsible for the consequences of submission of false information or documents.</li>
<li>Provide the company with any change relating to address, education, training, status, job responsibilities, skills, marital status, criminal charges, or any other information or circumstances which may affect his/her case for permanent residence.</li>
<li>Acknowledge that we are able to advise about immigration law at a particular point in time but are unable to predict future changes in the law.</li>
<li>Respond promptly to our requests for further information or documents whenever required.</li>
<li>Not hold us responsible for delays caused by your failure to promptly provide information or documents.</li>
<li>Establish high proficiency in English/French language by the requisite bands in IELTS/TEF test or any other test as laid down by the Immigration authorities (subject to change from time to time) in order to qualify under the program. Clearing IELTS / PTE with the suggested bands is solely the responsibility of the client.</li>
</ul>

<p>We will be under no obligation to submit your application to the Department or for the next stage until payment has been made in full of all fees due and payable for that stage.</p>
<p>The application no. will not be shared till the outcome is received; however, we will share the screen-shot every fortnight.</p>
<p>You are requested to pay the next installment on Positive Skill Assessment within <strong>10 days</strong> of receiving the positive assessment. Failure to do so will close the application from our end. For reopening the application there will be a fee of <strong>Rs. 10,000 + Taxes</strong> applicable.</p>
<p>The final decision on an application submitted to the Department is beyond our control. We cannot guarantee the success of any application. We will not be liable for any loss arising from changes to the law affecting your application which occurs after the application has been lodged.</p>
<p>If we have provided advice to you that, in our opinion, an application would be vexatious or grossly unfounded, then you will provide a written acknowledgment of the receipt of this advice. If, notwithstanding the advice, you still wish to lodge the application, the Client warrants that once LEAMSS is instructed in any case, all representations and contact with the relevant authorities will be made via LEAMSS, and at no time will the Client (or any agent of theirs) contact or make representations to any authorities with whom LEAMSS is dealing or with whom LEAMSS is about to deal.</p>
<p>The Client warrants that any information or documentation provided to LEAMSS shall be true and accurate and further the Client hereby indemnifies LEAMSS for any loss or damage LEAMSS may suffer directly or indirectly as a result of the Client's breach of this sub-clause — such loss or damage including but not limited to the legal costs of defending any civil claim or criminal penalty against LEAMSS arising from the Client's breach hereof.</p>
<p>The Client undertakes, on instructing LEAMSS, to promptly provide detailed information and documentation regarding the Client's personal details, qualifications, work experience and any other information or documentation that, in its sole discretion, LEAMSS may deem necessary in order to obtain a Visa for the Client. LEAMSS cannot guarantee published Australian Government visa processing times but undertakes to ensure that all applications are prepared, processed, and managed expeditiously on its part.</p>

<h3>Job Assistance / Post-Landing Services</h3>
<p>LEAMSS will also assist in Job Search and provide complete assistance in post-landing services with a ready guide to Australia. Post-landing assistance services include:</p>
<ul>
<li>* Airport pickup</li>
<li>Opening of bank account</li>
<li>* Temporary accommodation assistance</li>
<li>* Permanent accommodation assistance</li>
<li>To assist in registering with Medicare</li>
<li>Sending resume to top-level recruitment firms</li>
<li>Sharing the resume with our old references for job search</li>
<li>* Relocation assistance</li>
<li><strong>Personal Guide</strong> — One hour of personal orientation and Employment Readiness Course (by Australian resident)</li>
</ul>
<p><em>* Marked services will be charged a nominal fee; other services are free of cost.</em></p>

<h2>Annexure IV: Professional Fees and Refunds</h2>
<p>LEAMSS's professional fees are detailed in this contract.</p>
<p><strong>100% Refund on Professional Fees</strong> on Negative skill assessment / Visa Refusal — unless there was any kind of negative verification from Employer or for any false or misleading documents.</p>
<p>No refunds in case of withdrawing the application voluntarily, due to any reason after releasing the checklist and sharing the intellectual property. Also no refund if there is a rejection due to Medical Health Check-up or Negative Report from Police Clearance Department from local authorities of your home country, or each country travelled in the last 10 years.</p>
<p>The Client agrees to pay the balance of the fees due within the time frame specified in their nominated payment option. A receipt will be sent to the client on the same day of payment.</p>
<p>The application will be "on hold" if the client does not pay the second installment due on Positive Skill Assessment. LEAMSS will not share the outcome letter till the second payment is cleared, and has the right to cancel the application.</p>
<p>Application fees, which are payable by the client, are subject to change by the relevant authority. Notification will be sent to the client if such a change occurs.</p>
<p>The professional fees refund policy does <strong>not apply</strong> if the Skills, State/Territory or Visa application is rejected due to provision of false documentation or statement by the Client. In this event LEAMSS will retain 100% of all fees paid.</p>
<p>Before commencing our service, LEAMSS will question the Client to reveal if there is an ongoing or pending medical condition affecting a migrating family member. The professional fees refund policy does not apply if the application is rejected due to a medical condition affecting a migrating family member that was not detailed to the LEAMSS agent before commencing service. LEAMSS retains the right to terminate a contract where a client has withheld such information.</p>
<p>Before commencing service, LEAMSS will question the Client about previous and/or pending criminal convictions. The refund policy does not apply if rejection occurs due to such conviction not previously disclosed.</p>
<p>The refund policy does not apply where an application cannot continue due to a material change in migration law or Client personal circumstance, including but not limited to changes by Department of Home Affairs (DHA), nominated state/territory, or your relevant Skills Assessing Authority. This also includes changes in personal circumstance — character change and change of medical conditions.</p>
<p>If the client fails to meet the required English language level needed to have the visa approved, the professional fees refund policy does not apply.</p>
<p>LEAMSS's professional fees refund does not apply if the application is rejected on any of the grounds detailed in sub-clauses 4(B), 4(C), 4(D), 4(E), 4(F), 4(G), 4(H), 4(I), 4(J), conditions which LEAMSS has no capacity to control.</p>
<p>Refunds are 100% performance-based and are not payable unless the client's skills or visa application is rejected and the client's migration application cannot proceed and succeed. They will not be refundable in the event that the client decides not to continue the application prior to final decision.</p>
<p>LEAMSS has no control over the time taken to process the application once it has been received by the governing body and so cannot be held responsible for time taken for them to complete the case. Nor are we able to guarantee their final decisions on a case.</p>

<h2>5. Complaints</h2>
<p>In the event the Client wishes to complain regarding the service they have received, the client is able to send this complaint to <strong>Ladhani Education &amp; Migration Services Pvt Ltd — {{leamss_agent_email}}</strong>. We aim to respond to all complaints within <strong>4 days</strong> of receipt after conducting an internal investigation.</p>

<h2>6. Ending this Agreement</h2>
<p>We will automatically end this agreement if any circumstances arise that are beyond our or your control, and stop us or you from carrying out any of our or your responsibilities.</p>
<p>You may end this contract at any time by writing to us to tell us that you are ending your agreement. But you will be legally responsible for paying any money you owe us for our fees or extra fees. You will have to pay this money even if we have asked for any of these fees at the time you end this agreement.</p>
<p>This Client-Care letter contains the agreement between you and us. You do not have any rights arising from anything being included in this document. No changes to these conditions will apply unless they are in writing and signed by a Director of LEAMSS, division of Ladhani Education &amp; Migration Services Pvt Ltd. You are considered to have accepted the terms of this client-care letter once you go ahead with your case, by either signing this client-care letter or on payment of any part of our fees.</p>

<h3>Contact Protocol for our Office</h3>
<p>Please note that we aim to answer all client calls as soon as practicable. However, if we are busy, your call will be transferred to our office voicemail where you can leave a message explaining the reasons why you need to speak to us. We will return your call as soon as possible depending upon the nature of your query. All appointments have to be agreed with us in advance and any urgent appointments can be made by contacting our office by telephone/email.</p>
<p>Upon completion of your application, all Xerox sets will <strong>NOT</strong> be returned to you. We are obliged by law to keep a copy of your file for <strong>2 years</strong>. We keep the file on the understanding that we have the authority to destroy it 2 years after the conclusion of our service to you.</p>

<h2>7. Accepting this Agreement</h2>
<p>In line with international contract law, you will have accepted this agreement once you pay your deposit and act in line with the conditions in it. <strong>This Agreement is legally binding in the country you live in.</strong></p>

<h2>Annexure V: Migration Specialist Fee Payment — PROFESSIONAL FEE (LEAMSS)</h2>
<table class="fee-table">
<tr><th>Item</th><th>Amount (INR)</th></tr>
<tr><td>Total Professional Fee</td><td><strong>{{proposal_final_amount}}</strong></td></tr>
<tr><td>Payment Mode</td><td>{{payment_mode}}</td></tr>
<tr><td>Milestone 1 — Registration</td><td>{{milestone_1_amount}} &nbsp;|&nbsp; due {{milestone_1_date}}</td></tr>
<tr><td>Milestone 2 — On Positive Skill Assessment</td><td>{{milestone_2_amount}} &nbsp;|&nbsp; due {{milestone_2_date}}</td></tr>
<tr><td>Milestone 3 — On Visa Lodgement</td><td>{{milestone_3_amount}} &nbsp;|&nbsp; due {{milestone_3_date}}</td></tr>
</table>
<p><em>Extra fees at Stage 2: <strong>Rs. 19,000 + GST</strong> in case the applicant is converting the subclass from 189 visas to 190/491 visas (where the applicant was advised for 189 subclass). This fee is not applicable for applicants already applying for subclass 190/491.</em></p>
<p><em>Disbursements — Notary, Courier, Translation, Police Clearance, Medicals, English test etc. — all need to be paid directly by the client.</em></p>

<h2>Signatures</h2>
<table class="signature-table">
<tr>
<td><strong>SIGNED BY THE CLIENT</strong><br/>{{client_name}}<br/>Date: {{agreement_date}}</td>
<td><strong>SIGNED BY LEAMSS</strong><br/>{{agent_name}}<br/>For: Ladhani Education &amp; Migration Services Pvt Ltd</td>
</tr>
</table>

</div>"""


# =============================================================
# AUSTRALIA PROTECTION POLICY — same body + Protection Annexure
# =============================================================
PROTECTION_INSERT = """<h2>Annexure VI: LEAMSS Protection Policy ⭐</h2>
<p><strong>Under the LEAMSS Protection Policy</strong>, in addition to the Standard refund clause, the Client is entitled to:</p>
<ul>
<li><strong>100% Refund of Professional Fees</strong> if the visa is refused for any reason within LEAMSS's control.</li>
<li><strong>Free re-application support</strong> for one alternate pathway in the event of an unforeseen policy change affecting eligibility.</li>
<li><strong>Priority case handling</strong> with named senior consultant assigned for end-to-end case management.</li>
<li>Coverage of LEAMSS professional fees refund applies even where standard refund clauses 4(B) – 4(J) would otherwise exclude the case (excluding fraud, voluntary withdrawal, or material change to migration law).</li>
</ul>
<p>The Protection Policy fee is included in the Total Professional Fee above and is non-divisible. Once availed, the Protection Policy is non-transferable and applies only to the named Client and the visa subclass mentioned in this Agreement.</p>
"""

AUSTRALIA_PROTECTION = AUSTRALIA_STANDARD.replace(
    "Service Agreement — LEAMSS Immigration Services (Australia)",
    "Service Agreement — LEAMSS Immigration Services (Australia · Protection Policy)"
).replace(
    '<h2>Annexure V: Migration Specialist Fee Payment',
    PROTECTION_INSERT + '<h2>Annexure V: Migration Specialist Fee Payment'
)


# =============================================================
# CANADA EXPRESS ENTRY (FSW) — verbatim with same structure
# =============================================================
CANADA_EXPRESS_ENTRY = """<div class="agreement-doc">

<h1 class="title">Retainer Agreement — LEAMSS Immigration Services (Canada · Express Entry)</h1>
<p class="meta"><strong>Date of Agreement:</strong> {{agreement_date}} &nbsp;&nbsp;|&nbsp;&nbsp; <strong>Reference:</strong> {{pa_number}}</p>

<p>This Retainer Agreement is entered into between <strong>Ladhani Education &amp; Migration Services Pvt Ltd</strong> ("LEAMSS"), a member of the College of Immigration and Citizenship Consultants (CICC) — the regulator in Canada for immigration consultants — and the Client identified below.</p>

<h2>Client Details</h2>
<table class="client-details">
<tr><td><strong>Name</strong></td><td>{{client_name}}</td></tr>
<tr><td><strong>Date of Birth</strong></td><td>{{client_dob}}</td></tr>
<tr><td><strong>Address</strong></td><td>{{client_address}}</td></tr>
<tr><td><strong>Email</strong></td><td>{{client_email}}</td></tr>
<tr><td><strong>Phone</strong></td><td>{{client_phone}}</td></tr>
<tr><td><strong>Service</strong></td><td>Canada Express Entry — Federal Skilled Worker Program (PR)</td></tr>
</table>

<h2>1. Service Validity</h2>
<p>LEAMSS's professional service is valid for <strong>1 (one) year</strong> from the date of execution. Once an Invitation To Apply (ITA) is received within this period, the service continues until the visa-office decision on the application.</p>

<h2>2. LEAMSS Responsibilities</h2>
<ul>
<li>File for Educational Credential Assessment (ECA) on the client's behalf.</li>
<li>Provide step-by-step guidance for IELTS / CELPIP / TEF / TCF tests.</li>
<li>File an Express Entry profile and maintain it during the validity period.</li>
<li>File any related Provincial Nominee Program (PNP) application upon notification of interest.</li>
<li>Provide complete representation till the final visa decision.</li>
<li>Maintain confidentiality of all client information per CICC code of ethics.</li>
</ul>

<h2>3. Client Responsibilities</h2>
<ul>
<li>Provide all information and documents truthfully and in writing.</li>
<li>Notify changes in marital status, education, employment, address, criminal record.</li>
<li>Achieve required language proficiency (IELTS General / CELPIP / TEF / TCF) — solely the client's responsibility.</li>
<li>Provide the ECA fee, language test fee, biometric fee, and government PR fees directly.</li>
<li>Respond to LEAMSS requests within <strong>7 days</strong>; failing this, the file may be closed.</li>
</ul>

<h2>4. Billing &amp; Milestones</h2>
<table class="fee-table">
<tr><th>Item</th><th>Amount (INR)</th></tr>
<tr><td>Total Professional Fee</td><td><strong>{{proposal_final_amount}}</strong></td></tr>
<tr><td>Payment Mode</td><td>{{payment_mode}}</td></tr>
<tr><td>Milestone 1 — Registration</td><td>{{milestone_1_amount}} &nbsp;|&nbsp; due {{milestone_1_date}}</td></tr>
<tr><td>Milestone 2 — On / before</td><td>{{milestone_2_amount}} &nbsp;|&nbsp; due {{milestone_2_date}}</td></tr>
<tr><td>Milestone 3 — On Invitation To Apply (ITA)</td><td>{{milestone_3_amount}} &nbsp;|&nbsp; due {{milestone_3_date}}</td></tr>
</table>

<h2>5. Refund Policy</h2>
<p><strong>100% refund of professional fees if:</strong></p>
<ul>
<li>ECA returns ineligible (and client did not misrepresent qualifications).</li>
<li>Express Entry profile cannot be created due to point-deficit despite truthful information supplied at intake.</li>
</ul>
<p><strong>No refund where:</strong></p>
<ul>
<li>Client withdraws voluntarily after profile is created.</li>
<li>Application is refused due to false/misleading documentation.</li>
<li>Refusal due to medicals/police clearance/criminality/character grounds.</li>
<li>Refusal due to a material change in IRCC policy after lodgement.</li>
</ul>

<h2>6. Confidentiality, Force Majeure &amp; Dispute Resolution</h2>
<p>All client data is held in strict confidence per CICC norms. LEAMSS is not liable for delays caused by acts of God, government action, civil unrest, or pandemics. Any dispute shall be referred first to internal mediation; if unresolved, to the courts of Mumbai, India.</p>

<h2>7. Electronic Signature &amp; Binding Effect</h2>
<p>The Client agrees that an electronic signature carries the same legal weight as a wet-ink signature in line with the IT Act 2000 (India) and applicable international contract law. By signing electronically, the Client agrees to all terms above.</p>

<h2>Signatures</h2>
<table class="signature-table">
<tr>
<td><strong>SIGNED BY THE CLIENT</strong><br/>{{client_name}}<br/>Date: {{agreement_date}}</td>
<td><strong>SIGNED BY LEAMSS</strong><br/>{{agent_name}}<br/>CICC RCIC Registered</td>
</tr>
</table>

</div>"""


def _detect(body):
    return sorted(set(re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", body)))


SEEDS = [
    {"name": "Australia · PR · Standard", "country": "Australia", "visa_category": "PR (Skilled Migration)", "policy_variant": "Standard", "body_html": AUSTRALIA_STANDARD, "is_active": True, "notes": "Verbatim Australia Standard Skilled Migration agreement (subclasses 189/190/491)."},
    {"name": "Australia · PR · Protection Policy", "country": "Australia", "visa_category": "PR (Skilled Migration)", "policy_variant": "Protection", "body_html": AUSTRALIA_PROTECTION, "is_active": True, "notes": "Premium variant — adds Annexure VI Protection Policy with full refund + alternate pathway."},
    {"name": "Canada · PR · Express Entry", "country": "Canada", "visa_category": "PR (Express Entry)", "policy_variant": "Standard", "body_html": CANADA_EXPRESS_ENTRY, "is_active": True, "notes": "Federal Skilled Worker / Express Entry CICC retainer."},
]


async def seed():
    upserted = 0
    for s in SEEDS:
        key = {"country": s["country"], "visa_category": s["visa_category"], "policy_variant": s["policy_variant"]}
        existing = await templates_col.find_one(key, {"_id": 0, "id": 1, "version": 1})
        if existing:
            new_version = (existing.get("version") or 1) + 1
            await templates_col.update_one(key, {"$set": {
                "name": s["name"], "body_html": s["body_html"],
                "placeholders": _detect(s["body_html"]),
                "notes": s["notes"], "is_active": True,
                "version": new_version,
                "updated_at": datetime.now(timezone.utc),
            }})
            print(f"♻️  updated to v{new_version}: {s['name']}")
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
