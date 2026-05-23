"""Phase 6.10.2 — Professional Report Renderer.

Generates a branded LEAMSS Assessment Report PDF from a frozen snapshot.

Brand:
  • Primary blue:  #1E3A8A  (deep professional blue)
  • Accent blue:   #2563EB  (vibrant brand blue)
  • Accent indigo: #4338CA  (section dividers)
  • Accent gold:   #F59E0B  (highlight / tagline)
  • Body charcoal: #1F2937
  • Tagline:       "We Value Emotions"
  • Company:       Ladhani Education & Migration Services Pvt. Ltd.
  • Website:       www.leamss.com  |  Email: rohit@leamss.com
  • Phone:         1800-210-2427
  • Office:        Office no 10, Londhe Compound, Mumbai (Thane) — 400602

Section structure (per Sir's spec):
  1. Cover Page (logo · tagline · client name · date · reference)
  2. Executive Summary (best country, score)
  3. Client Profile Snapshot
  4. Per-Country Sections (full occupation + visa pathways + points + state demand)
  5. Process Flow + Cost Estimator
  6. Country Guide (Part 3 — currently a stub)
  7. Indicative Document Checklist (admin/CM detailed list comes later)
  8. Disclaimer
  9. LEAMSS Contact

All data comes from the snapshot — never live KB.
"""
import io
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)

# ─── Brand constants ─────────────────────────────────────────────────────────
BRAND_PRIMARY = colors.HexColor("#1E3A8A")
BRAND_ACCENT = colors.HexColor("#2563EB")
BRAND_INDIGO = colors.HexColor("#4338CA")
BRAND_GOLD = colors.HexColor("#F59E0B")
BRAND_CHARCOAL = colors.HexColor("#1F2937")
BRAND_LIGHT_GREY = colors.HexColor("#F3F4F6")
BRAND_BORDER = colors.HexColor("#E5E7EB")
BRAND_EMERALD = colors.HexColor("#059669")
BRAND_AMBER = colors.HexColor("#D97706")

COMPANY = "Ladhani Education & Migration Services Pvt. Ltd."
TAGLINE = "We Value Emotions"
WEBSITE = "www.leamss.com"
EMAIL_ADDR = "rohit@leamss.com"
PHONE = "1800-210-2427"
OFFICE = "Office no 10, Londhe Compound, Mumbai (Thane) — 400602"


# ─────────────────────────────────────────────────────────────────────────────
# Styles
# ─────────────────────────────────────────────────────────────────────────────
def _build_styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle("cover_title", parent=base["Title"],
                                       fontName="Helvetica-Bold", fontSize=48,
                                       leading=54, textColor=BRAND_PRIMARY, alignment=0, spaceAfter=8),
        "cover_subtitle": ParagraphStyle("cover_subtitle", parent=base["Title"],
                                          fontName="Helvetica-Bold", fontSize=20,
                                          leading=26, textColor=BRAND_ACCENT, alignment=0, spaceAfter=24),
        "tagline": ParagraphStyle("tagline", fontName="Helvetica-Oblique",
                                   fontSize=13, leading=16, textColor=BRAND_GOLD,
                                   alignment=0, spaceAfter=6),
        "company": ParagraphStyle("company", fontName="Helvetica-Bold",
                                   fontSize=11, textColor=BRAND_CHARCOAL, spaceAfter=2),
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=18,
                              leading=22, textColor=BRAND_PRIMARY, spaceBefore=12, spaceAfter=8),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13,
                              leading=18, textColor=BRAND_ACCENT, spaceBefore=8, spaceAfter=6),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11,
                              leading=14, textColor=BRAND_INDIGO, spaceBefore=6, spaceAfter=4),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10,
                                leading=14, textColor=BRAND_CHARCOAL, spaceAfter=4),
        "body_small": ParagraphStyle("body_small", fontName="Helvetica", fontSize=8.5,
                                      leading=11.5, textColor=BRAND_CHARCOAL),
        "highlight": ParagraphStyle("highlight", fontName="Helvetica-Bold",
                                     fontSize=10, leading=14, textColor=BRAND_PRIMARY,
                                     backColor=BRAND_LIGHT_GREY, borderPadding=6,
                                     spaceBefore=4, spaceAfter=4),
        "disclaimer": ParagraphStyle("disclaimer", fontName="Helvetica-Oblique",
                                      fontSize=8, leading=11, textColor=colors.HexColor("#6B7280"),
                                      backColor=BRAND_LIGHT_GREY, borderPadding=6),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Page frame: brand header + footer with logo / page number
# ─────────────────────────────────────────────────────────────────────────────
def _draw_page_frame(canvas, doc):
    page_w, page_h = A4
    canvas.saveState()

    # Top brand strip
    canvas.setFillColor(BRAND_PRIMARY)
    canvas.rect(0, page_h - 1.4 * cm, page_w, 1.4 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(1.6 * cm, page_h - 0.95 * cm, "LEAMSS · Assessment Report")
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.setFillColor(BRAND_GOLD)
    canvas.drawString(1.6 * cm, page_h - 1.25 * cm, TAGLINE)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(page_w - 1.6 * cm, page_h - 0.95 * cm,
                            f"Report Reference: {getattr(doc, '_snapshot_ref', '—')}")
    canvas.drawRightString(page_w - 1.6 * cm, page_h - 1.25 * cm,
                            f"Generated: {getattr(doc, '_generated_date', '')}")

    # Footer
    canvas.setFillColor(BRAND_INDIGO)
    canvas.rect(0, 0, 1.2 * cm, page_h - 1.4 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.6 * cm, 0.7 * cm, f"{COMPANY}  ·  {WEBSITE}  ·  {EMAIL_ADDR}  ·  {PHONE}")
    canvas.setFillColor(BRAND_ACCENT)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawRightString(page_w - 1.6 * cm, 0.7 * cm, f"Page {doc.page}")
    canvas.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# Section builders — each takes snapshot data and yields flowables
# ─────────────────────────────────────────────────────────────────────────────
def _section_cover(snap: Dict[str, Any], styles) -> List:
    client = snap.get("client") or {}
    best = snap.get("best_country") or {}
    flow = []
    flow.append(Spacer(1, 4 * cm))
    flow.append(Paragraph("ASSESSMENT", styles["cover_title"]))
    flow.append(Paragraph("REPORT", styles["cover_title"]))
    flow.append(Spacer(1, 0.6 * cm))
    flow.append(Paragraph(f"<b>Prepared for:</b> {_safe(client.get('name'))}", styles["h2"]))
    flow.append(Paragraph(f"Best country recommendation: <b>{_safe(best.get('country_name') or best.get('country_code'))}</b>", styles["body"]))
    flow.append(Paragraph(f"Indicative score: <b>{_safe(best.get('total'))}</b> points", styles["body"]))
    flow.append(Spacer(1, 1.4 * cm))
    flow.append(Paragraph(TAGLINE, styles["tagline"]))
    flow.append(Paragraph(COMPANY, styles["company"]))
    flow.append(Paragraph(f"{WEBSITE}  ·  {EMAIL_ADDR}  ·  {PHONE}", styles["body_small"]))
    flow.append(Paragraph(OFFICE, styles["body_small"]))
    flow.append(Spacer(1, 0.4 * cm))
    flow.append(Paragraph(
        f"Report Reference: <b>{snap.get('snapshot_id')}</b>  ·  Generated on {snap.get('generated_on_human')}",
        styles["body_small"],
    ))
    flow.append(PageBreak())
    return flow


def _section_executive_summary(snap, styles):
    best = snap.get("best_country") or {}
    countries = snap.get("countries") or []
    flow = [Paragraph("SECTION 1 — EXECUTIVE SUMMARY", styles["h1"])]
    flow.append(Paragraph(
        f"Based on the profile information provided, the strongest pathway is "
        f"<b>{_safe(best.get('country_name'))}</b> with an indicative score of "
        f"<b>{_safe(best.get('total'))}</b> against a pass mark of "
        f"<b>{_safe(best.get('pass_mark'))}</b>.",
        styles["body"]))
    if len(countries) > 1:
        rows = [["Country", "Score", "Pass Mark", "Verdict"]]
        for c in countries:
            rows.append([
                f"{_flag(c.get('country_code'))} {_safe(c.get('country_name') or c.get('country_code'))}",
                str(_safe(c.get("total"))),
                str(_safe(c.get("pass_mark"))),
                "✓ ELIGIBLE" if (c.get("total") or 0) >= (c.get("pass_mark") or 0) else "Below threshold",
            ])
        t = Table(rows, colWidths=[5.5 * cm, 2.5 * cm, 2.5 * cm, 4 * cm])
        t.setStyle(_table_style())
        flow.append(t)
    flow.append(Spacer(1, 0.4 * cm))
    flow.append(Paragraph(
        "<b>Note:</b> Eligibility is based on information provided by the client at the time of this assessment "
        "and on the latest verified Knowledge Base data of our internal sources. Final outcomes depend on the "
        "skill assessment, official policy at the time of application, and supporting documentation.",
        styles["disclaimer"]))
    flow.append(PageBreak())
    return flow


def _section_client_profile(snap, styles):
    client = snap.get("client") or {}
    profile = snap.get("profile_snapshot") or {}
    primary = profile.get("primary_applicant") or {}
    spouse = profile.get("spouse")
    flow = [Paragraph("SECTION 2 — CLIENT PROFILE", styles["h1"])]
    rows = [
        ["Full Name", _safe(client.get("name"))],
        ["Email", _safe(client.get("email"))],
        ["Phone", _safe(client.get("phone"))],
        ["Marital status", _safe(profile.get("marital_status"))],
        ["Age", _safe((primary.get("personal") or {}).get("age"))],
        ["Highest Qualification", _safe((primary.get("education") or {}).get("highest_qualification"))],
        ["IELTS Overall", _safe(((primary.get("language") or {}).get("scores") or {}).get("overall"))],
        ["Years of Experience", _safe((primary.get("professional") or {}).get("years_experience_total"))],
        ["Current Profession", _safe((primary.get("professional") or {}).get("current_profession"))],
    ]
    if spouse:
        rows.append(["Spouse — Migrating?", "Yes"])
        rows.append(["Spouse Age", _safe((spouse.get("personal") or {}).get("age"))])
        rows.append(["Spouse Qualification", _safe((spouse.get("education") or {}).get("highest_qualification"))])
    t = Table([["Field", "Value"]] + rows, colWidths=[6 * cm, 9.5 * cm])
    t.setStyle(_table_style())
    flow.append(t)
    flow.append(PageBreak())
    return flow


def _section_country(country: Dict[str, Any], snap, styles, idx: int):
    cc = country.get("country_code")
    flag = _flag(cc)
    flow = [Paragraph(f"SECTION 3.{idx} — {flag} {_safe(country.get('country_name') or cc)} · ASSESSMENT", styles["h1"])]
    # Eligibility headline
    total = country.get("total")
    pass_mark = country.get("pass_mark")
    meets_threshold = (total or 0) >= (pass_mark or 0)
    verdict_text = (
        "<b>You meet the threshold.</b>"
        if meets_threshold
        else "Below threshold — see &quot;How to gain points&quot; recommendations."
    )
    eligible_text = (
        f"<b>Indicative Score: {total} points</b> against pass mark <b>{pass_mark}</b>. {verdict_text}"
    )
    flow.append(Paragraph(eligible_text, styles["highlight"]))

    # Occupation block (full detail per Sir's directive)
    occ = country.get("occupation") or {}
    if occ:
        flow.append(Paragraph("Occupation Details", styles["h2"]))
        rows = [
            ["Code", _safe(occ.get("code"))],
            ["Title", _safe(occ.get("title"))],
            ["Classification", f"{_safe(occ.get('classification_type'))} {_safe(occ.get('classification_version'))}"],
            ["Skill Level", _safe(occ.get("skill_level"))],
            ["Unit Group", _safe((occ.get("hierarchy") or {}).get("unit_group_name"))],
            ["Assessing Authority", _safe((occ.get("assessing_authority") or {}).get("name"))],
            ["Pathway List", ", ".join((occ.get("visa_pathways") or {}).get("pathway_lists") or []) or "—"],
        ]
        t = Table([["Field", "Value"]] + rows, colWidths=[5 * cm, 10.5 * cm])
        t.setStyle(_table_style())
        flow.append(t)

        if occ.get("description"):
            flow.append(Paragraph("Description", styles["h3"]))
            flow.append(Paragraph(_safe(occ.get("description")), styles["body"]))

        if occ.get("typical_tasks"):
            flow.append(Paragraph("Typical Tasks", styles["h3"]))
            for task in (occ.get("typical_tasks") or [])[:12]:
                flow.append(Paragraph(f"• {_safe(task)}", styles["body_small"]))

    # Visa eligibility table
    vp = occ.get("visa_pathways") or {}
    visas = vp.get("visa_eligibility") or []
    if visas:
        flow.append(Paragraph("Visa Pathway Eligibility", styles["h2"]))
        rows = [["Subclass", "Eligible", "List", "Notes"]]
        for v in visas:
            rows.append([
                _safe(v.get("visa_subclass")),
                "✓ Yes" if v.get("eligible") else "✗ No",
                _safe(v.get("list")),
                _safe(v.get("notes"))[:60],
            ])
        t = Table(rows, colWidths=[2.8 * cm, 2.2 * cm, 2.5 * cm, 7.5 * cm])
        t.setStyle(_table_style())
        flow.append(t)

    # State demand (AU)
    state_elig = occ.get("state_territory_eligibility") or []
    if state_elig:
        flow.append(Paragraph("State / Territory Demand", styles["h2"]))
        rows = [["State", "Demand", "190 Eligible", "491 Eligible"]]
        for s in state_elig:
            rows.append([
                _safe(s.get("state")),
                _safe(s.get("demand", "")).replace("_", " ").title() if s.get("demand") else "—",
                "✓" if s.get("sc190") else "—",
                "✓" if s.get("sc491") else "—",
            ])
        t = Table(rows, colWidths=[3.5 * cm, 4 * cm, 4 * cm, 4 * cm])
        t.setStyle(_table_style())
        flow.append(t)

    # Points breakdown
    breakdown = country.get("breakdown") or {}
    if breakdown:
        flow.append(Paragraph("Points Breakdown", styles["h2"]))
        rows = [["Factor", "Points"]]
        for k, v in breakdown.items():
            pts = v.get("points") if isinstance(v, dict) else v
            rows.append([k.replace("_", " ").title(), str(pts or 0)])
        rows.append(["TOTAL", str(total or 0)])
        t = Table(rows, colWidths=[10 * cm, 5.5 * cm])
        t.setStyle(_table_style(highlight_last=True))
        flow.append(t)

    flow.append(PageBreak())
    return flow


def _section_process_and_cost(snap, styles):
    flow = [Paragraph("SECTION 4 — PROCESS FLOW & COST ESTIMATOR", styles["h1"])]
    steps = [
        ("1. Pre-Assessment", "Submit profile + supporting documents for review."),
        ("2. Admin Approval", "Internal verification + first approval."),
        ("3. AI Proposal Generation", "Personalised proposal with detailed pricing + timeline."),
        ("4. Consent + Main Fee Payment", "Sign agreement + complete payment via secure portal."),
        ("5. Case Manager Assignment", "Dedicated CM contacts the client + provides detailed checklist."),
        ("6. Skill Assessment Lodgement", "Documents lodged with the relevant assessing authority."),
        ("7. EOI / Express Entry Profile", "Lodge expression of interest with immigration authorities."),
        ("8. State / Provincial Nomination", "(Where applicable) submit nomination application."),
        ("9. Invitation to Apply (ITA)", "Receive invitation from immigration authorities."),
        ("10. Visa Application + Medicals + PCC", "Complete medicals, police clearance, lodge visa application."),
        ("11. Decision + Grant", "Visa outcome — grant or further requests."),
        ("12. Post-Landing Support", "Optional CM support for arrival, settlement, employment."),
    ]
    rows = [["Step", "Description"]]
    rows.extend(steps)
    t = Table(rows, colWidths=[5 * cm, 10.5 * cm])
    t.setStyle(_table_style())
    flow.append(t)

    # Cost estimator (placeholder — real data comes from fee_calculator)
    fees = snap.get("cost_estimate")
    if fees:
        flow.append(Paragraph("Indicative Cost Breakdown", styles["h2"]))
        rows = [["Component", "Currency", "Amount"]]
        for item in fees.get("items", []):
            rows.append([_safe(item.get("label")), _safe(item.get("currency")), _safe(item.get("amount"))])
        rows.append(["TOTAL", _safe(fees.get("total_currency")), _safe(fees.get("total_amount"))])
        t = Table(rows, colWidths=[8 * cm, 3 * cm, 4.5 * cm])
        t.setStyle(_table_style(highlight_last=True))
        flow.append(t)
        flow.append(Paragraph(
            "Indicative only — actuals are confirmed in your personalised proposal at Step 3.",
            styles["disclaimer"]))
    flow.append(PageBreak())
    return flow


def _section_country_guide(snap, styles):
    """Phase 6.10 Part 3 stub — Country Guide content is filled in via the
    admin-managed Country Guide collection later. For now, render the structure
    so the report layout is final.
    """
    flow = [Paragraph("SECTION 5 — COUNTRY GUIDE", styles["h1"])]
    guides = snap.get("country_guides") or []
    if not guides:
        flow.append(Paragraph(
            "Country guide content is currently being verified by our admin team. "
            "The next version of this report will include job market overview, average salary, "
            "best locations, citizenship pathway, and key benefits.",
            styles["disclaimer"]))
        flow.append(PageBreak())
        return flow
    for g in guides:
        flow.append(Paragraph(f"{_flag(g.get('country_code'))} {_safe(g.get('country_name'))}", styles["h2"]))
        if g.get("job_market"):
            flow.append(Paragraph("Job Market", styles["h3"]))
            flow.append(Paragraph(_safe(g.get("job_market")), styles["body"]))
        if g.get("salary"):
            flow.append(Paragraph("Average Salary", styles["h3"]))
            flow.append(Paragraph(_safe(g.get("salary")), styles["body"]))
        if g.get("best_locations"):
            flow.append(Paragraph("Best Locations", styles["h3"]))
            flow.append(Paragraph(_safe(g.get("best_locations")), styles["body"]))
        if g.get("citizenship_pathway"):
            flow.append(Paragraph("Citizenship Pathway", styles["h3"]))
            flow.append(Paragraph(_safe(g.get("citizenship_pathway")), styles["body"]))
    flow.append(PageBreak())
    return flow


def _section_indicative_checklist(snap, styles):
    flow = [Paragraph("SECTION 6 — INDICATIVE DOCUMENT CHECKLIST", styles["h1"])]
    flow.append(Paragraph(
        "This is a high-level indicative checklist only. A detailed, occupation- and country-specific "
        "checklist will be provided by your Case Manager <b>after main fees are paid and your case is assigned.</b>",
        styles["highlight"]))
    docs = [
        ("Identity", ["Passport (all pages)", "National ID", "Birth certificate"]),
        ("Education", ["Degree certificates", "Mark sheets / transcripts", "Equivalency assessment (if applicable)"]),
        ("Experience", ["Reference letters from employers", "Pay slips", "Tax records / Form 16"]),
        ("Language", ["IELTS / PTE / CELPIP / TEF result"]),
        ("Skills Assessment", ["Self-declaration", "Reference letters on company letterhead", "Resume"]),
        ("Health & Character", ["Police Clearance Certificate (PCC)", "Medical examination report (post-invitation)"]),
        ("Family (if applicable)", ["Marriage certificate", "Children birth certificates", "Spouse's documents (same as above)"]),
    ]
    for category, items in docs:
        flow.append(Paragraph(category, styles["h3"]))
        for item in items:
            flow.append(Paragraph(f"• {item}", styles["body_small"]))
    flow.append(PageBreak())
    return flow


def _section_disclaimer(snap, styles):
    flow = [Paragraph("SECTION 7 — IMPORTANT DISCLAIMER", styles["h1"])]
    flow.append(Paragraph(
        f"This report is generated on <b>{snap.get('generated_on_human')}</b> based on the profile information "
        "and supporting details provided by the client. Migration law, occupation lists, points-test rules, "
        "fees, and processing times <b>change frequently and without notice.</b> Accuracy cannot be guaranteed. "
        "Clients are strongly advised to confirm current rules with official sources or via professional "
        "migration counselling before lodging any application.",
        styles["body"]))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph(
        "This report does not constitute legal or migration advice. It is an indicative assessment based on the "
        "data captured at the time of generation. LEAMSS / Ladhani Education & Migration Services Pvt. Ltd. is "
        "not responsible for outcomes arising from external policy changes, document discrepancies, or "
        "factors beyond the information provided.",
        styles["disclaimer"]))
    flow.append(PageBreak())
    return flow


def _section_contact(snap, styles):
    flow = [Paragraph("LEAMSS — CONTACT", styles["h1"])]
    flow.append(Paragraph(TAGLINE, styles["tagline"]))
    flow.append(Spacer(1, 0.4 * cm))
    flow.append(Paragraph(COMPANY, styles["company"]))
    rows = [
        ["Website", WEBSITE],
        ["Email", EMAIL_ADDR],
        ["Phone", PHONE],
        ["Office", OFFICE],
    ]
    t = Table(rows, colWidths=[4 * cm, 11.5 * cm])
    t.setStyle(_table_style(no_header=True))
    flow.append(t)
    return flow


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _table_style(highlight_last: bool = False, no_header: bool = False) -> TableStyle:
    base = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (0, 0), (-1, -1), BRAND_CHARCOAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1 if not no_header else 0), (-1, -1), [colors.white, BRAND_LIGHT_GREY]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, BRAND_BORDER),
    ]
    if not no_header:
        base.extend([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    if highlight_last:
        base.extend([
            ("BACKGROUND", (0, -1), (-1, -1), BRAND_ACCENT),
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ])
    return TableStyle(base)


def _safe(v) -> str:
    if v is None or v == "":
        return "—"
    return str(v)


_FLAGS = {"AU": "🇦🇺", "CA": "🇨🇦", "NZ": "🇳🇿", "UK": "🇬🇧", "US": "🇺🇸"}


def _flag(cc: str) -> str:
    return _FLAGS.get((cc or "").upper(), "")


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────
def render_pdf(snapshot: Dict[str, Any]) -> bytes:
    """Render a snapshot into a branded PDF and return raw bytes."""
    buffer = io.BytesIO()
    styles = _build_styles()

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=2.0 * cm, bottomMargin=1.4 * cm,
        title=f"LEAMSS Assessment Report — {snapshot.get('snapshot_id')}",
        author=COMPANY,
    )
    doc._snapshot_ref = snapshot.get("snapshot_id", "—")[:14]
    doc._generated_date = snapshot.get("generated_on_human", "")

    main_frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        id="main", showBoundary=0,
    )
    doc.addPageTemplates([
        PageTemplate(id="branded", frames=[main_frame], onPage=_draw_page_frame),
    ])

    story: List = []
    story.extend(_section_cover(snapshot, styles))
    story.extend(_section_executive_summary(snapshot, styles))
    story.extend(_section_client_profile(snapshot, styles))
    for idx, country in enumerate(snapshot.get("countries") or [], start=1):
        story.extend(_section_country(country, snapshot, styles, idx))
    story.extend(_section_process_and_cost(snapshot, styles))
    story.extend(_section_country_guide(snapshot, styles))
    story.extend(_section_indicative_checklist(snapshot, styles))
    story.extend(_section_disclaimer(snapshot, styles))
    story.extend(_section_contact(snapshot, styles))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def now_human() -> str:
    return datetime.now().strftime("%d %B %Y · %I:%M %p")
