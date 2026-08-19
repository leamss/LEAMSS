"""Settings-driven client report email (LEAMSS) — premium responsive design.

`build_report_email(settings, ...)` renders a polished, email-client-safe HTML
(table layout + inline CSS) using the admin-editable Email Settings. Safe fallbacks
throughout so a partially-filled settings doc still renders cleanly.
"""
from __future__ import annotations

from html import escape
from typing import Any, Dict, List, Optional, Tuple

# ── Palette ───────────────────────────────────────────────────────
TEAL = "#12433B"       # deep premium teal
TEAL2 = "#1C5A4E"
ORANGE = "#D4633F"
GOLD = "#C99A3B"
SAFFRON = "#FF9933"
GREEN = "#138808"
INK = "#1F2A37"
SLATE = "#5B6B7B"
MUTED = "#94a3b8"
BORDER = "#E4EAE8"
LIGHT = "#F6F8F7"
CREAM = "#FFFDF5"
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "Arial, 'Helvetica Neue', Helvetica, sans-serif"


def _paras(text: str, color: str = SLATE, size: int = 14) -> str:
    if not text:
        return ""
    blocks = [b.strip() for b in text.replace("\r\n", "\n").split("\n\n") if b.strip()]
    return "".join(
        f'<p style="margin:0 0 14px;color:{color};font-size:{size}px;line-height:1.75;font-family:{SANS};">'
        f'{escape(b).replace(chr(10), "<br>")}</p>' for b in blocks
    )


def _section_title(text: str) -> str:
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:26px 0 12px;"><tr>'
            f'<td style="width:4px;background:{ORANGE};border-radius:3px;">&nbsp;</td>'
            f'<td style="padding-left:10px;font-family:{SERIF};font-size:17px;font-weight:700;color:{TEAL};">{escape(text)}</td>'
            f'</tr></table>')


def _services(items: List[str]) -> str:
    items = [str(x).strip() for x in (items or []) if str(x).strip()]
    if not items:
        return ""
    cells = ""
    for i in range(0, len(items), 2):
        pair = items[i:i + 2]
        tds = ""
        for it in pair:
            tds += (f'<td width="50%" valign="top" style="padding:5px 8px 5px 0;">'
                    f'<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
                    f'<td valign="top" style="color:{GREEN};font-size:14px;font-weight:800;padding-right:7px;">✓</td>'
                    f'<td style="color:{INK};font-size:13px;line-height:1.5;font-family:{SANS};">{escape(it)}</td>'
                    f'</tr></table></td>')
        if len(pair) == 1:
            tds += '<td width="50%"></td>'
        cells += f"<tr>{tds}</tr>"
    return (f'{_section_title("What You Get With LEAMSS")}'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="background:{LIGHT};border:1px solid {BORDER};border-radius:12px;padding:12px 16px;">{cells}</table>')


def _offer(s: Dict[str, Any]) -> str:
    if not s.get("offer_enabled", True):
        return ""
    badge = escape(s.get("offer_badge") or "Special Offer")
    title = escape(s.get("offer_title") or "Exclusive Professional Fee Offer")
    regular = escape(s.get("offer_regular_fee") or "")
    price = escape(s.get("offer_price") or "")
    savings = escape(s.get("offer_savings") or "")
    valid = escape(s.get("offer_valid_till") or "")
    note = escape(s.get("offer_note") or "")

    regular_html = (f'<div style="color:#cbd5d1;font-size:13px;font-family:{SANS};">Regular Fees: '
                    f'<span style="text-decoration:line-through;">{regular}</span></div>') if regular else ""
    price_html = (f'<div style="color:#ffffff;font-family:{SERIF};font-size:30px;font-weight:800;line-height:1.2;margin-top:2px;">{price}</div>') if price else ""
    savings_html = (f'<span style="display:inline-block;background:{ORANGE};color:#fff;font-family:{SANS};'
                    f'font-weight:800;font-size:14px;padding:8px 20px;border-radius:24px;margin-top:12px;">🎉 {savings}</span>') if savings else ""
    valid_html = (f'<div style="color:{GOLD};font-family:{SANS};font-size:12px;font-weight:700;margin-top:12px;letter-spacing:0.3px;">⏳ OFFER VALID TILL {valid.upper()}</div>') if valid else ""
    note_html = (f'<div style="color:#b9c6c2;font-family:{SANS};font-size:11px;margin-top:8px;line-height:1.5;">{note}</div>') if note else ""

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:26px 0;">
      <tr><td style="background:{TEAL};border:2px solid {GOLD};border-radius:16px;padding:24px 26px;text-align:center;">
        <span style="display:inline-block;background:{GOLD};color:{TEAL};font-family:{SANS};font-size:11px;font-weight:800;letter-spacing:1px;text-transform:uppercase;padding:6px 16px;border-radius:20px;">{badge}</span>
        <div style="color:#ffffff;font-family:{SERIF};font-size:18px;font-weight:700;margin:14px 0 12px;">{title}</div>
        {regular_html}
        {price_html}
        {savings_html}
        {valid_html}
        {note_html}
      </td></tr>
    </table>"""


def _kv_card(title: str, rows: List[Tuple[str, str]], emoji: str = "") -> str:
    body = "".join(
        f'<tr><td style="padding:3px 12px 3px 0;color:{SLATE};font-size:12px;white-space:nowrap;font-family:{SANS};">{escape(k)}</td>'
        f'<td style="padding:3px 0;color:{INK};font-size:12px;font-weight:700;font-family:{SANS};">{escape(str(v))}</td></tr>'
        for k, v in rows if v
    )
    if not body:
        return ""
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border:1px solid {BORDER};border-radius:12px;background:#fff;margin:10px 0;"><tr><td style="padding:14px 18px;">'
            f'<div style="color:{TEAL};font-family:{SANS};font-size:13px;font-weight:800;margin-bottom:8px;">{emoji} {escape(title)}</div>'
            f'<table role="presentation" cellpadding="0" cellspacing="0">{body}</table>'
            f'</td></tr></table>')


def _intl(banks: List[Dict[str, Any]]) -> str:
    banks = [b for b in (banks or []) if (b.get("label") or b.get("details"))]
    if not banks:
        return ""
    rows_html = ""
    for i in range(0, len(banks), 2):
        pair = banks[i:i + 2]
        tds = ""
        for b in pair:
            label = escape(b.get("label") or "Account")
            details = escape(b.get("details") or "").replace("\n", "<br>")
            tds += (f'<td width="50%" valign="top" style="padding:6px;">'
                    f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {BORDER};border-radius:10px;background:#fff;">'
                    f'<tr><td style="padding:11px 13px;">'
                    f'<div style="color:{ORANGE};font-family:{SANS};font-size:12px;font-weight:800;margin-bottom:5px;">{label}</div>'
                    f'<div style="color:{SLATE};font-family:{SANS};font-size:11px;line-height:1.65;">{details}</div>'
                    f'</td></tr></table></td>')
        if len(pair) == 1:
            tds += '<td width="50%"></td>'
        rows_html += f"<tr>{tds}</tr>"
    return (f'<div style="color:{TEAL};font-family:{SANS};font-size:13px;font-weight:800;margin:16px 0 2px;">🌍 International Bank Accounts</div>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows_html}</table>')


def _payment(s: Dict[str, Any], backend_url: str) -> str:
    if not s.get("payment_enabled", True):
        return ""
    intro = escape(s.get("payment_intro") or "To proceed, please find our payment details below. You can pay by Credit Card / NEFT / IMPS / UPI, or scan our QR code (also attached).")
    link = (s.get("payment_link") or "").strip()
    link_btn = ""
    if link:
        link_btn = (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:6px auto 18px;"><tr>'
                    f'<td style="background:{ORANGE};border-radius:28px;">'
                    f'<a href="{escape(link)}" style="display:inline-block;padding:13px 34px;color:#fff;text-decoration:none;'
                    f'font-family:{SANS};font-size:15px;font-weight:700;">💳&nbsp; Pay Securely Online</a></td></tr></table>')

    b = s.get("bank_domestic") or {}
    domestic = _kv_card("Domestic Bank (India) — NEFT / IMPS / RTGS", [
        ("Account Name", b.get("account_name")), ("Account No.", b.get("account_number")),
        ("IFSC", b.get("ifsc")), ("Bank", b.get("bank_name")),
        ("Branch", b.get("branch")), ("Type", b.get("account_type")),
    ], emoji="🇮🇳")

    upi = (s.get("upi_id") or "").strip()
    qr_url = f"{backend_url.rstrip('/')}/api/email-settings/asset/qr" if (backend_url and s.get("qr_file_id")) else ""
    qr_block = ""
    if qr_url or upi:
        img = (f'<img src="{qr_url}" alt="Scan &amp; Pay QR" width="190" '
               f'style="width:190px;max-width:72%;border-radius:12px;display:block;margin:0 auto;" />') if qr_url else ""
        upi_line = (f'<div style="color:{INK};font-family:{SANS};font-size:13px;font-weight:700;margin-top:10px;">UPI ID: {escape(upi)}</div>') if upi else ""
        qr_block = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0;"><tr>'
                    f'<td align="center" style="background:{LIGHT};border:1px solid {BORDER};border-radius:12px;padding:18px;">'
                    f'<div style="color:{TEAL};font-family:{SANS};font-size:13px;font-weight:800;margin-bottom:12px;">📱 Scan &amp; Pay (UPI)</div>'
                    f'{img}{upi_line}'
                    f'<div style="color:{MUTED};font-family:{SANS};font-size:10px;margin-top:8px;">GPay · PhonePe · Paytm · BHIM &nbsp;·&nbsp; QR also attached</div>'
                    f'</td></tr></table>')

    return (f'{_section_title("Payment Details")}'
            f'<p style="margin:0 0 14px;color:{SLATE};font-size:13px;line-height:1.65;font-family:{SANS};">{intro}</p>'
            f'{link_btn}{domestic}{_intl(s.get("banks_international") or [])}{qr_block}')


def build_report_email(
    settings: Optional[Dict[str, Any]], *, client_name: str,
    occupation: Optional[str] = None, code: Optional[str] = None,
    points: Optional[dict] = None, sender_name: str = "LEAMSS", backend_url: str = "",
) -> Tuple[str, str, str]:
    s = settings or {}
    cname = " ".join((client_name or "Applicant").split())
    subject = (s.get("subject_template") or "Your Australia PR Pre-Assessment Report — {name}").replace("{name}", cname)
    outcome = escape(s.get("outcome_title") or "Your Australia Migration Profile Pre-Assessment Outcome is Positive")
    body_html = _paras(s.get("body_message") or "Please find your Pre-Assessment report attached.")

    # Report summary card
    summary = ""
    occ_txt = " · ".join([x for x in [escape(str(code)) if code else "", escape(occupation) if occupation else ""] if x])
    pts = ""
    if points and isinstance(points, dict):
        chips = "".join(
            f'<td style="padding:0 5px;"><table role="presentation" cellpadding="0" cellspacing="0"><tr>'
            f'<td style="background:#fff;border:1px solid {BORDER};border-radius:10px;padding:8px 14px;text-align:center;">'
            f'<div style="color:{MUTED};font-family:{SANS};font-size:10px;font-weight:700;">SUBCLASS {sc}</div>'
            f'<div style="color:{TEAL};font-family:{SERIF};font-size:20px;font-weight:800;">{points[sc]}</div></td></tr></table></td>'
            for sc in ("189", "190", "491") if points.get(sc) is not None)
        if chips:
            pts = f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:10px;"><tr>{chips}</tr></table>'
    if occ_txt or pts:
        occ_html = (f'<div style="color:{SLATE};font-family:{SANS};font-size:12px;">Nominated Occupation</div>'
                    f'<div style="color:{INK};font-family:{SANS};font-size:15px;font-weight:700;">{occ_txt}</div>') if occ_txt else ""
        summary = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                   f'style="background:{LIGHT};border:1px solid {BORDER};border-radius:12px;margin:18px 0;"><tr>'
                   f'<td style="padding:16px 18px;">{occ_html}{pts}</td></tr></table>')

    services = _services(s.get("services_list") or [])

    gov = s.get("gov_charges") or []
    gov_html = ""
    if gov:
        gr = "".join(
            f'<tr><td style="padding:4px 0;color:{SLATE};font-size:12px;font-family:{SANS};border-bottom:1px solid {BORDER};">{escape(g.get("label",""))}</td>'
            f'<td style="padding:4px 0;text-align:right;color:{INK};font-size:12px;font-weight:700;font-family:{SANS};border-bottom:1px solid {BORDER};">{escape(g.get("amount",""))}</td></tr>'
            for g in gov if g.get("label"))
        gov_html = (f'{_section_title("Estimated Australian Government Charges")}'
                    f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {BORDER};border-radius:12px;background:#fff;"><tr><td style="padding:14px 18px;">'
                    f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{gr}</table>'
                    f'<div style="color:{MUTED};font-family:{SANS};font-size:10px;margin-top:8px;">Set by the Australian Government · subject to change without notice.</div>'
                    f'</td></tr></table>')

    offer = _offer(s)
    payment = _payment(s, backend_url)

    # Indicative-assessment callout (editable disclaimer)
    indic = escape(s.get("indicative_note") or
                   "This is an indicative assessment. Our migration team will be glad to walk you through the report and plan your next steps. Simply reply to this email or call us on the numbers below.")
    indic_block = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:24px 0 6px;"><tr>'
                   f'<td style="background:{CREAM};border-left:4px solid {ORANGE};border-radius:8px;padding:14px 18px;">'
                   f'<div style="color:{INK};font-family:{SANS};font-size:13px;line-height:1.65;font-style:italic;">{indic}</div>'
                   f'</td></tr></table>')

    calendly = (s.get("calendly_link") or "").strip()
    cta = ""
    if calendly:
        cta = (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:16px auto 6px;"><tr>'
               f'<td style="background:{TEAL};border-radius:30px;">'
               f'<a href="{escape(calendly)}" style="display:inline-block;padding:15px 38px;color:#fff;text-decoration:none;font-family:{SANS};font-size:15px;font-weight:700;">📅&nbsp; Book a Free Consultation</a>'
               f'</td></tr></table>'
               f'<div style="text-align:center;color:{MUTED};font-family:{SANS};font-size:11px;margin-bottom:6px;">Pick a slot that suits you</div>')

    closing = escape(s.get("closing") or "Warm Regards,\nLEAMSS – Ladhani Education & Migration Services Pvt. Ltd.").replace("\n", "<br>")
    phone = escape(s.get("contact_phone") or "+91 77188 82427")
    cemail = escape(s.get("contact_email") or "info@leamss.com")
    website = escape(s.get("website") or "www.leamss.com")

    tags = []
    if s.get("attach_report", True):
        tags.append("Pre-Assessment Report")
    if s.get("attach_sla") and s.get("sla_file_id"):
        tags.append("Service Level Agreement")
    if s.get("attach_resume"):
        tags.append("Your Resume")
    if s.get("qr_file_id"):
        tags.append("Payment QR")
    attach_note = ""
    if tags:
        chips = "".join(
            f'<span style="display:inline-block;background:{LIGHT};border:1px solid {BORDER};color:{SLATE};'
            f'font-family:{SANS};font-size:11px;padding:5px 12px;border-radius:16px;margin:3px 5px 3px 0;">📎 {escape(t)}</span>'
            for t in tags)
        attach_note = f'<div style="margin:18px 0 0;">{chips}</div>'

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#e9edeb;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#e9edeb;padding:20px 0;">
   <tr><td align="center">
    <table role="presentation" width="620" cellpadding="0" cellspacing="0" style="width:620px;max-width:96%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(18,67,59,0.12);">
      <!-- tricolour accent -->
      <tr><td style="height:5px;background:{SAFFRON};font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="height:5px;background:#ffffff;font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="height:5px;background:{GREEN};font-size:0;line-height:0;">&nbsp;</td></tr>
      <!-- header -->
      <tr><td style="background:{TEAL};padding:26px 34px;">
        <div style="color:#ffffff;font-family:{SERIF};font-size:21px;font-weight:800;letter-spacing:0.3px;">Ladhani Education &amp; Migration Services</div>
        <div style="color:{GOLD};font-family:{SANS};font-size:12px;font-weight:600;margin-top:5px;letter-spacing:0.4px;">GLOBAL EDUCATION &amp; IMMIGRATION EXPERTS &nbsp;·&nbsp; YOUR SUCCESS, OUR DREAM</div>
      </td></tr>
      <!-- body -->
      <tr><td style="padding:30px 34px;">
        <p style="margin:0 0 14px;color:{INK};font-family:{SANS};font-size:15px;">Dear {escape(cname)},</p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 18px;"><tr>
          <td style="background:#eaf6ee;border:1px solid #cfe9d8;border-radius:12px;padding:14px 18px;">
            <span style="color:{GREEN};font-family:{SANS};font-size:15px;font-weight:800;">✅ {outcome}</span>
          </td></tr></table>
        {body_html}
        {summary}
        {services}
        {offer}
        {gov_html}
        {payment}
        {indic_block}
        {cta}
        {attach_note}
        <p style="margin:24px 0 0;color:{SLATE};font-family:{SANS};font-size:13px;line-height:1.75;">{closing}</p>
      </td></tr>
      <!-- footer -->
      <tr><td style="background:{TEAL};padding:20px 34px;">
        <div style="color:#ffffff;font-family:{SANS};font-size:12px;font-weight:700;">{escape(sender_name)}</div>
        <div style="color:#b9c6c2;font-family:{SANS};font-size:11px;margin-top:6px;">☎ {phone} &nbsp;·&nbsp; ✉ {cemail} &nbsp;·&nbsp; 🌐 {website}</div>
        <div style="color:#8ea39d;font-family:{SANS};font-size:10px;margin-top:12px;line-height:1.6;">
          This assessment is indicative, based on the information provided and current publicly available migration rules.
          Australian Government eligibility criteria, invitation rounds, visa decisions and charges are controlled solely by the
          Australian Government and may change without prior notice. Not legal or migration advice under contract until formally engaged.
        </div>
      </td></tr>
    </table>
   </td></tr>
  </table>
</body></html>"""

    # plain text
    lines = [f"Dear {cname},", "", s.get("outcome_title") or "Your Australia Migration Profile Pre-Assessment Outcome is Positive", "",
             (s.get("body_message") or "Please find your Pre-Assessment report attached.")]
    if occ_txt:
        lines += ["", f"Occupation: {code or ''} {occupation or ''}".strip()]
    if points and isinstance(points, dict):
        cp = " · ".join([f"{sc}: {points[sc]}" for sc in ("189", "190", "491") if points.get(sc) is not None])
        if cp:
            lines += [f"Indicative points — {cp}"]
    if s.get("offer_enabled", True):
        lines += ["", (s.get("offer_badge") or "Special Offer"),
                  f"Regular: {s.get('offer_regular_fee','')}  |  Offer: {s.get('offer_price','')}  {s.get('offer_savings','')}".strip(),
                  (f"Valid till {s.get('offer_valid_till')}" if s.get("offer_valid_till") else "")]
    if s.get("payment_link"):
        lines += ["", f"Pay online: {s.get('payment_link')}"]
    if s.get("upi_id"):
        lines += [f"UPI: {s.get('upi_id')}"]
    lines += ["", (s.get("indicative_note") or "This is an indicative assessment. Reply to this email or call us to discuss next steps.")]
    if calendly:
        lines += ["", f"Book a consultation: {calendly}"]
    lines += ["", (s.get("closing") or "Warm Regards,\nLEAMSS")]
    plain = "\n".join([str(x) for x in lines if x is not None])
    return subject, html, plain


def _list_block(title: str, items: List[str], accent: str, numbered: bool = False) -> str:
    items = [str(x).strip() for x in (items or []) if str(x).strip()]
    if not items:
        return ""
    rows = ""
    for i, it in enumerate(items, 1):
        marker = (f'<td valign="top" style="width:22px;color:{accent};font-family:{SANS};font-size:13px;font-weight:800;">{i}.</td>'
                  if numbered else
                  f'<td valign="top" style="width:18px;color:{accent};font-family:{SANS};font-size:14px;font-weight:800;">•</td>')
        rows += (f'<tr>{marker}'
                 f'<td style="padding:4px 0 4px 4px;color:{SLATE};font-size:13px;line-height:1.6;font-family:{SANS};">{escape(it)}</td></tr>')
    return (f'{_section_title(title)}'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border:1px solid {BORDER};border-radius:12px;background:#fff;"><tr><td style="padding:12px 16px;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
            f'</td></tr></table>')


def build_not_eligible_email(
    settings: Optional[Dict[str, Any]], *, client_name: str, verdict: Dict[str, Any],
    occupation: Optional[str] = None, code: Optional[str] = None,
    sender_name: str = "LEAMSS", backend_url: str = "",
) -> Tuple[str, str, str]:
    """Warm, honest 'not eligible (yet)' email — improvable or age-blocked variant.

    `verdict` is the block produced by core.eligibility.classify_eligibility().
    """
    s = settings or {}
    cname = " ".join((client_name or "Applicant").split())
    v = verdict or {}
    kind = v.get("verdict")
    is_age = kind == "ineligible_age"

    subject = (f"Your Australia PR Pre-Assessment Outcome — {cname}")
    headline = v.get("headline") or ("Your Migration Eligibility Outcome")
    sub = v.get("sub") or ""

    banner_bg = "#B44A3A" if is_age else "#B7791F"
    banner_icon = "✗" if is_age else "⚠"

    intro = (f"Thank you for choosing LEAMSS. We have carefully reviewed your profile against the current Australian "
             f"skilled migration rules. We believe in complete transparency, so here is an honest assessment of where "
             f"you stand today"
             + (" — along with the alternative pathways worth exploring." if is_age
                else " — and a clear action plan to help you become eligible."))

    occ_txt = " · ".join([x for x in [escape(str(code)) if code else "", escape(occupation) if occupation else ""] if x])
    occ_html = ""
    if occ_txt:
        occ_html = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{LIGHT};'
                    f'border:1px solid {BORDER};border-radius:12px;margin:16px 0;"><tr><td style="padding:14px 18px;">'
                    f'<div style="color:{SLATE};font-family:{SANS};font-size:12px;">Nominated Occupation</div>'
                    f'<div style="color:{INK};font-family:{SANS};font-size:15px;font-weight:700;">{occ_txt}</div>'
                    f'<div style="color:{SLATE};font-family:{SANS};font-size:12px;margin-top:8px;">Best pathway '
                    f'Subclass {escape(str(v.get("best_subclass") or "—"))} · Indicative score '
                    f'<b style="color:{INK};">{v.get("best_points") or 0}</b> / pass mark {v.get("pass_mark") or 65}</div>'
                    f'</td></tr></table>')

    reasons = _list_block("Why You Are Not Eligible Right Now", v.get("reasons") or [], banner_bg)
    improvements = _list_block("How To Become Eligible — Your Action Plan", v.get("improvements") or [], TEAL, numbered=True)
    alternatives = _list_block("Alternative Pathways Worth Exploring", v.get("alternatives") or [], TEAL)

    calendly = (s.get("calendly_link") or "").strip()
    cta = ""
    if calendly:
        cta = (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:20px auto 6px;"><tr>'
               f'<td style="background:{TEAL};border-radius:30px;">'
               f'<a href="{escape(calendly)}" style="display:inline-block;padding:15px 38px;color:#fff;text-decoration:none;font-family:{SANS};font-size:15px;font-weight:700;">📅&nbsp; Book a Free Consultation</a>'
               f'</td></tr></table>'
               f'<div style="text-align:center;color:{MUTED};font-family:{SANS};font-size:11px;margin-bottom:6px;">Let our experts map your best route</div>')

    closing = escape(s.get("closing") or "Warm Regards,\nLEAMSS – Ladhani Education & Migration Services Pvt. Ltd.").replace("\n", "<br>")
    phone = escape(s.get("contact_phone") or "+91 77188 82427")
    cemail = escape(s.get("contact_email") or "info@leamss.com")
    website = escape(s.get("website") or "www.leamss.com")

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#e9edeb;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#e9edeb;padding:20px 0;"><tr><td align="center">
    <table role="presentation" width="620" cellpadding="0" cellspacing="0" style="width:620px;max-width:96%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(18,67,59,0.12);">
      <tr><td style="height:5px;background:{SAFFRON};font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="height:5px;background:#ffffff;font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="height:5px;background:{GREEN};font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="background:{TEAL};padding:26px 34px;">
        <div style="color:#ffffff;font-family:{SERIF};font-size:21px;font-weight:800;">Ladhani Education &amp; Migration Services</div>
        <div style="color:{GOLD};font-family:{SANS};font-size:12px;font-weight:600;margin-top:5px;letter-spacing:0.4px;">GLOBAL EDUCATION &amp; IMMIGRATION EXPERTS &nbsp;·&nbsp; YOUR SUCCESS, OUR DREAM</div>
      </td></tr>
      <tr><td style="padding:30px 34px;">
        <p style="margin:0 0 14px;color:{INK};font-family:{SANS};font-size:15px;">Dear {escape(cname)},</p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 18px;"><tr>
          <td style="background:{banner_bg};border-radius:12px;padding:14px 18px;">
            <span style="color:#fff;font-family:{SANS};font-size:15px;font-weight:800;">{banner_icon} {escape(headline)}</span>
            <div style="color:#f5e6df;font-family:{SANS};font-size:12px;margin-top:4px;">{escape(sub)}</div>
          </td></tr></table>
        <p style="margin:0 0 14px;color:{SLATE};font-size:14px;line-height:1.75;font-family:{SANS};">{escape(intro)}</p>
        {occ_html}
        {reasons}
        {improvements}
        {alternatives}
        {cta}
        <div style="margin:22px 0 0;"><span style="display:inline-block;background:{LIGHT};border:1px solid {BORDER};color:{SLATE};font-family:{SANS};font-size:11px;padding:5px 12px;border-radius:16px;">📎 Detailed Pre-Assessment Report (PDF)</span></div>
        <p style="margin:24px 0 0;color:{SLATE};font-family:{SANS};font-size:13px;line-height:1.75;">{closing}</p>
      </td></tr>
      <tr><td style="background:{TEAL};padding:20px 34px;">
        <div style="color:#ffffff;font-family:{SANS};font-size:12px;font-weight:700;">{escape(sender_name)}</div>
        <div style="color:#b9c6c2;font-family:{SANS};font-size:11px;margin-top:6px;">☎ {phone} &nbsp;·&nbsp; ✉ {cemail} &nbsp;·&nbsp; 🌐 {website}</div>
        <div style="color:#8ea39d;font-family:{SANS};font-size:10px;margin-top:12px;line-height:1.6;">
          This assessment is indicative, based on the information provided and current publicly available migration rules.
          Australian Government eligibility criteria may change without prior notice. Not legal or migration advice under contract until formally engaged.
        </div>
      </td></tr>
    </table>
   </td></tr></table>
</body></html>"""

    lines = [f"Dear {cname},", "", headline, sub, "", intro]
    if occ_txt:
        lines += ["", f"Occupation: {code or ''} {occupation or ''}".strip(),
                  f"Best pathway Subclass {v.get('best_subclass') or '-'} · score {v.get('best_points') or 0}/{v.get('pass_mark') or 65}"]
    for grp, title in ((v.get("reasons"), "Why not eligible"), (v.get("improvements"), "How to become eligible"),
                       (v.get("alternatives"), "Alternative pathways")):
        if grp:
            lines += ["", title + ":"] + [f"- {x}" for x in grp]
    if calendly:
        lines += ["", f"Book a consultation: {calendly}"]
    lines += ["", (s.get("closing") or "Warm Regards,\nLEAMSS")]
    plain = "\n".join([str(x) for x in lines if x is not None])
    return subject, html, plain


def build_resume_request_email(
    settings: Optional[Dict[str, Any]], *, client_name: str, upload_url: str,
    sender_name: str = "LEAMSS",
) -> Tuple[str, str, str]:
    """Email asking the client to upload their resume via a secure link."""
    s = settings or {}
    cname = " ".join((client_name or "Applicant").split())
    subject = f"Action needed: Upload your resume for your Australia PR assessment — {cname}"

    intro = ("We're excited to prepare your personalised Australia PR Pre-Assessment. To complete it accurately, our team "
             "needs your latest resume/CV. It only takes a minute — just click the secure button below and upload your "
             "resume. No login or password is required.")
    steps = _list_block("What Happens Next", [
        "Click the button and upload your resume (PDF or Word).",
        "Our AI + migration team analyse it and match your best ANZSCO occupation.",
        "You receive your detailed, personalised Pre-Assessment report by email.",
    ], TEAL, numbered=True)

    btn = (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px auto 8px;"><tr>'
           f'<td style="background:{ORANGE};border-radius:30px;">'
           f'<a href="{escape(upload_url)}" style="display:inline-block;padding:16px 42px;color:#fff;text-decoration:none;font-family:{SANS};font-size:16px;font-weight:800;">📄&nbsp; Upload My Resume</a>'
           f'</td></tr></table>'
           f'<div style="text-align:center;color:{MUTED};font-family:{SANS};font-size:11px;margin-bottom:6px;">'
           f'Secure link · or copy &amp; paste: <span style="color:{SLATE};">{escape(upload_url)}</span></div>')

    closing = escape(s.get("closing") or "Warm Regards,\nLEAMSS – Ladhani Education & Migration Services Pvt. Ltd.").replace("\n", "<br>")
    phone = escape(s.get("contact_phone") or "+91 77188 82427")
    cemail = escape(s.get("contact_email") or "info@leamss.com")
    website = escape(s.get("website") or "www.leamss.com")

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#e9edeb;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#e9edeb;padding:20px 0;"><tr><td align="center">
    <table role="presentation" width="620" cellpadding="0" cellspacing="0" style="width:620px;max-width:96%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(18,67,59,0.12);">
      <tr><td style="height:5px;background:{SAFFRON};font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="height:5px;background:#ffffff;font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="height:5px;background:{GREEN};font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="background:{TEAL};padding:26px 34px;">
        <div style="color:#ffffff;font-family:{SERIF};font-size:21px;font-weight:800;">Ladhani Education &amp; Migration Services</div>
        <div style="color:{GOLD};font-family:{SANS};font-size:12px;font-weight:600;margin-top:5px;letter-spacing:0.4px;">GLOBAL EDUCATION &amp; IMMIGRATION EXPERTS</div>
      </td></tr>
      <tr><td style="padding:30px 34px;">
        <p style="margin:0 0 14px;color:{INK};font-family:{SANS};font-size:15px;">Dear {escape(cname)},</p>
        <p style="margin:0 0 14px;color:{SLATE};font-size:14px;line-height:1.75;font-family:{SANS};">{escape(intro)}</p>
        {btn}
        {steps}
        <p style="margin:20px 0 0;color:{SLATE};font-size:13px;line-height:1.7;font-family:{SANS};">If you have any trouble uploading, simply reply to this email with your resume attached and we'll take care of the rest.</p>
        <p style="margin:24px 0 0;color:{SLATE};font-family:{SANS};font-size:13px;line-height:1.75;">{closing}</p>
      </td></tr>
      <tr><td style="background:{TEAL};padding:20px 34px;">
        <div style="color:#ffffff;font-family:{SANS};font-size:12px;font-weight:700;">{escape(sender_name)}</div>
        <div style="color:#b9c6c2;font-family:{SANS};font-size:11px;margin-top:6px;">☎ {phone} &nbsp;·&nbsp; ✉ {cemail} &nbsp;·&nbsp; 🌐 {website}</div>
      </td></tr>
    </table>
   </td></tr></table>
</body></html>"""

    plain = "\n".join([
        f"Dear {cname},", "", intro, "", f"Upload your resume here: {upload_url}", "",
        "What happens next:", "1. Upload your resume (PDF or Word).",
        "2. Our team matches your best ANZSCO occupation.", "3. You receive your personalised Pre-Assessment report.",
        "", "Or simply reply to this email with your resume attached.", "",
        (s.get("closing") or "Warm Regards,\nLEAMSS"),
    ])
    return subject, html, plain



# ══════════════════════════════════════════════════════════════════════════
# CUSTOM TEMPLATE ENGINE — user-authored email templates with {placeholders}
# ══════════════════════════════════════════════════════════════════════════

# Placeholders the user can drop into a template's subject / body.
TEMPLATE_PLACEHOLDERS = [
    {"token": "{client_name}", "desc": "Client's full name"},
    {"token": "{occupation}", "desc": "Nominated occupation title"},
    {"token": "{code}", "desc": "ANZSCO occupation code"},
    {"token": "{points}", "desc": "Best indicative points score"},
    {"token": "{best_subclass}", "desc": "Best visa subclass (189/190/491)"},
    {"token": "{pass_mark}", "desc": "Pass mark (65)"},
    {"token": "{reasons}", "desc": "Bulleted list of eligibility reasons"},
    {"token": "{improvements}", "desc": "Bulleted 'how to become eligible' steps"},
    {"token": "{alternatives}", "desc": "Bulleted alternative pathways"},
    {"token": "{upload_link}", "desc": "Secure resume-upload link"},
    {"token": "{consultant_name}", "desc": "Assigned consultant / sender name"},
    {"token": "{calendly_link}", "desc": "Consultation booking link"},
    {"token": "{offer_badge}", "desc": "Offer badge (e.g. Independence Day Special)"},
    {"token": "{offer_price}", "desc": "Discounted offer price"},
    {"token": "{offer_regular_fee}", "desc": "Regular (pre-offer) fee"},
    {"token": "{offer_savings}", "desc": "Savings amount"},
    {"token": "{offer_valid_till}", "desc": "Offer deadline"},
    {"token": "{payment_link}", "desc": "Online payment link"},
    {"token": "{upi_id}", "desc": "UPI ID for payment"},
    {"token": "{company}", "desc": "Company name (LEAMSS)"},
    {"token": "{phone}", "desc": "Contact phone"},
    {"token": "{email}", "desc": "Contact email"},
    {"token": "{website}", "desc": "Website"},
]


def _fmt_list_lines(items: List[Any]) -> str:
    return "\n".join(f"• {str(x).strip()}" for x in (items or []) if str(x).strip())


def apply_placeholders(text: str, ctx: Dict[str, Any]) -> str:
    """Replace {token} occurrences with context values (lists → bullet lines)."""
    if not text:
        return ""
    out = text
    for key, val in (ctx or {}).items():
        token = "{" + key + "}"
        if token not in out:
            continue
        if isinstance(val, (list, tuple)):
            rep = _fmt_list_lines(val)
        elif val is None:
            rep = ""
        else:
            rep = str(val)
        out = out.replace(token, rep)
    return out


def _body_text_to_html(text: str) -> str:
    """Convert a plain-text body (with newlines and '• ' bullets) into safe HTML."""
    if not text:
        return ""
    blocks = [b for b in text.replace("\r\n", "\n").split("\n\n")]
    html_parts: List[str] = []
    for block in blocks:
        lines = [ln for ln in block.split("\n")]
        bullet_lines = [ln for ln in lines if ln.strip().startswith("• ")]
        if bullet_lines and len(bullet_lines) == len([ln for ln in lines if ln.strip()]):
            items = "".join(
                f'<li style="margin:0 0 6px;color:{SLATE};font-size:14px;line-height:1.6;font-family:{SANS};">'
                f'{escape(ln.strip()[2:].strip())}</li>' for ln in bullet_lines
            )
            html_parts.append(f'<ul style="margin:0 0 14px;padding-left:20px;">{items}</ul>')
        else:
            safe = escape(block).replace("\n", "<br>")
            html_parts.append(
                f'<p style="margin:0 0 14px;color:{SLATE};font-size:14px;line-height:1.75;font-family:{SANS};">{safe}</p>'
            )
    return "".join(html_parts)


def _brand_shell(inner_html: str, sender_name: str, settings: Optional[Dict[str, Any]]) -> str:
    s = settings or {}
    phone = escape(s.get("contact_phone") or "+91 77188 82427")
    cemail = escape(s.get("contact_email") or "info@leamss.com")
    website = escape(s.get("website") or "www.leamss.com")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#e9edeb;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#e9edeb;padding:20px 0;"><tr><td align="center">
    <table role="presentation" width="620" cellpadding="0" cellspacing="0" style="width:620px;max-width:96%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(18,67,59,0.12);">
      <tr><td style="height:5px;background:{SAFFRON};font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="height:5px;background:#ffffff;font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="height:5px;background:{GREEN};font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="background:{TEAL};padding:26px 34px;">
        <div style="color:#ffffff;font-family:{SERIF};font-size:21px;font-weight:800;">Ladhani Education &amp; Migration Services</div>
        <div style="color:{GOLD};font-family:{SANS};font-size:12px;font-weight:600;margin-top:5px;letter-spacing:0.4px;">GLOBAL EDUCATION &amp; IMMIGRATION EXPERTS</div>
      </td></tr>
      <tr><td style="padding:30px 34px;">{inner_html}</td></tr>
      <tr><td style="background:{TEAL};padding:20px 34px;">
        <div style="color:#ffffff;font-family:{SANS};font-size:12px;font-weight:700;">{escape(sender_name or 'LEAMSS')}</div>
        <div style="color:#b9c6c2;font-family:{SANS};font-size:11px;margin-top:6px;">☎ {phone} &nbsp;·&nbsp; ✉ {cemail} &nbsp;·&nbsp; 🌐 {website}</div>
      </td></tr>
    </table>
   </td></tr></table>
</body></html>"""


def render_custom_email(template: Dict[str, Any], ctx: Dict[str, Any], *,
                        sender_name: str = "LEAMSS", settings: Optional[Dict[str, Any]] = None
                        ) -> Tuple[str, str, str]:
    """Render a user-authored template (subject + body with {placeholders}) into a branded email."""
    subject = apply_placeholders(template.get("subject") or "", ctx).strip() or "A message from LEAMSS"
    body_raw = apply_placeholders(template.get("body") or "", ctx)
    inner = _body_text_to_html(body_raw)
    html = _brand_shell(inner, sender_name, settings)
    plain = body_raw
    return subject, html, plain
