"""Phase 19.4c — JSA Vacancy Report PDF parser (Internet Vacancy Index).

Parses the monthly JSA IVI PDF (5 pages) into a single `VacancySnapshot` record.

Defensive design: PDF table extraction via pdfplumber is brittle on JSA layouts,
so we use a regex-first approach on extracted text, with table extraction as a
cross-check fallback. ANZSCO major-group rows + state rows are pattern-matched
from the page-4 summary sheet which has stable formatting across monthly releases.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

import pdfplumber

SOURCE_NAME_FMT = "JSA Internet Vacancy Index {period}"
SOURCE_URL = "https://www.jobsandskills.gov.au/data/internet-vacancy-index"
DATA_QUALITY = "official_govt_data"

# State labels exactly as they appear on the IVI summary sheet (page 4).
_STATE_CODES = {
    "Australia": "TOTAL",
    "New South Wales": "NSW",
    "Victoria": "VIC",
    "Queensland": "QLD",
    "South Australia": "SA",
    "Western Australia": "WA",
    "Tasmania": "TAS",
    "Northern Territory": "NT",
    "Australian Capital Territory": "ACT",
}

# ANZSCO 1-digit major groups exactly as labelled on the IVI summary sheet.
_ANZSCO_MAJOR_GROUPS = [
    "Managers",
    "Professionals",
    "Technicians and Trades Workers",
    "Community and Personal Service Workers",
    "Clerical and Administrative Workers",
    "Sales Workers",
    "Machinery Operators and Drivers",
    "Labourers",
]


def _parse_int(s: str) -> Optional[int]:
    if not s:
        return None
    s = s.replace(",", "").replace(" ", "").replace("\u00a0", "")
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def _parse_period_and_release(text: str) -> tuple[str, str, str]:
    """Extract reporting period + release-date from page 1 header text.
    Returns (period, period_iso_first_day, next_release_iso_or_blank)."""
    period_m = re.search(r"Vacancy Report\s+(\w+\s+\d{4})", text)
    period = period_m.group(1) if period_m else ""
    period_iso = ""
    if period:
        try:
            period_iso = datetime.strptime(period.strip(), "%B %Y").date().replace(day=1).isoformat()
        except ValueError:
            period_iso = ""
    next_m = re.search(r"next IVI release is scheduled for\s+(\d+\s+\w+\s+\d{4})", text)
    next_release = ""
    if next_m:
        try:
            next_release = datetime.strptime(next_m.group(1), "%d %B %Y").date().isoformat()
        except ValueError:
            pass
    return period, period_iso, next_release


def _parse_national_summary(text: str) -> Dict[str, Any]:
    """Extract national total + monthly Δ% + annual Δ% from page-1 narrative."""
    out: Dict[str, Any] = {}
    # National total appears as "212,000\nOnline\nJob Advertisements" near the top.
    total_m = re.search(r"\b(\d{1,3}(?:,\d{3})+)\b\s+(?:Online|\n+Online)", text)
    if total_m:
        out["national_ads"] = _parse_int(total_m.group(1))
    # Narrative will mention "decreased X%" or "increased X%" + "over the year"
    mon_m = re.search(r"(decreased|increased|down|up)\s+(\d+(?:\.\d+)?)%\s+(?:nationally|in\s+\w+|over the month|monthly)", text, re.IGNORECASE)
    if mon_m:
        sign = -1 if mon_m.group(1).lower() in ("decreased", "down") else 1
        out["monthly_change_pct"] = sign * float(mon_m.group(2))
    return out


def _parse_state_table(text: str) -> Dict[str, Dict[str, Any]]:
    """Parse the page-4 state summary table.

    Page-4 text shape (per state row):
        "{State}        {Ads}     {Δ-num}  {▲/▼} {Δ-%}   {AnnΔ-num}  {▲/▼} {AnnΔ-%}"
    """
    rows: Dict[str, Dict[str, Any]] = {}
    pattern = re.compile(
        r"^\s*("
        + "|".join(re.escape(k) for k in _STATE_CODES)
        + r")\s+"
        + r"([\d,]+)\s+"                              # ads
        + r"(-?[\d,]+)\s+[▲▼]?\s*"                    # monthly Δ num
        + r"(-?\d+(?:\.\d+)?)%\s+"                    # monthly Δ %
        + r"(-?[\d,]+)\s+[▲▼]?\s*"                    # annual Δ num
        + r"(-?\d+(?:\.\d+)?)%",                      # annual Δ %
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        name, ads, m_num, m_pct, y_num, y_pct = m.groups()
        rows[_STATE_CODES[name]] = {
            "ads": _parse_int(ads),
            "monthly_change_num": _parse_int(m_num),
            "monthly_change_pct": float(m_pct),
            "annual_change_num": _parse_int(y_num),
            "annual_change_pct": float(y_pct),
        }
    return rows


def _parse_major_group_table(text: str) -> Dict[str, Dict[str, Any]]:
    """Parse the page-4 ANZSCO major-group summary table (same row shape as states)."""
    rows: Dict[str, Dict[str, Any]] = {}
    pattern = re.compile(
        r"^\s*("
        + "|".join(re.escape(g) for g in _ANZSCO_MAJOR_GROUPS)
        + r")\s+"
        + r"([\d,]+)\s+"
        + r"(-?[\d,]+)\s+[▲▼]?\s*"
        + r"(-?\d+(?:\.\d+)?)%\s+"
        + r"(-?[\d,]+)\s+[▲▼]?\s*"
        + r"(-?\d+(?:\.\d+)?)%",
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        name, ads, m_num, m_pct, y_num, y_pct = m.groups()
        rows[name] = {
            "ads": _parse_int(ads),
            "monthly_change_num": _parse_int(m_num),
            "monthly_change_pct": float(m_pct),
            "annual_change_num": _parse_int(y_num),
            "annual_change_pct": float(y_pct),
        }
    return rows


def _parse_featured_occupation(text: str) -> Dict[str, str]:
    """Extract the monthly featured-occupation narrative title + first paragraph."""
    # Featured-occupation header pattern: "Keeping to the timetable: Strong demand for X"
    m = re.search(r"(?:Keeping to the timetable|Featured occupation|Spotlight)\s*[:\-]?\s*(.+?)\n", text)
    title = ""
    if m:
        title = m.group(1).strip()
        # If "Strong demand for X", extract the occupation name only
        sub = re.search(r"(?:demand|focus|need)\s+for\s+([\w\s,\-/&]+)", title, re.IGNORECASE)
        if sub:
            title = sub.group(1).strip().rstrip(".")
    # First paragraph after the header (~300 chars)
    narrative = ""
    if m:
        rest = text[m.end():]
        para = re.split(r"\n\s*\n", rest, maxsplit=1)[0] if rest else ""
        narrative = " ".join(para.split())[:400]
    return {"title": title, "narrative": narrative}


def parse_pdf(path: str) -> Iterator[Dict[str, Any]]:
    """Yield a single snapshot dict for the given vacancy PDF."""
    with pdfplumber.open(path) as pdf:
        pages_text: List[str] = [(p.extract_text() or "") for p in pdf.pages]

    full_text = "\n".join(pages_text)

    period, period_iso, next_release = _parse_period_and_release(pages_text[0])
    nat = _parse_national_summary(pages_text[0])

    # State + major-group tables live on page 4 of the standard layout.
    page4 = pages_text[3] if len(pages_text) > 3 else full_text
    states = _parse_state_table(page4)
    majors = _parse_major_group_table(page4)

    # Fallbacks + cross-fills: state-table TOTAL row is the most reliable source
    # for monthly/annual change %s, so prefer those over narrative regex.
    if states.get("TOTAL"):
        nat.setdefault("national_ads", states["TOTAL"]["ads"])
        nat["national_ads"] = nat.get("national_ads") or states["TOTAL"]["ads"]
        # Always overwrite with TOTAL row values — they're the canonical figures.
        nat["monthly_change_pct"] = states["TOTAL"].get("monthly_change_pct")
        nat["annual_change_pct"] = states["TOTAL"].get("annual_change_pct")

    # Re-search for next_release across all pages (text can wrap to page 5)
    if not next_release:
        full = "\n".join(pages_text)
        next_m = re.search(r"next IVI release is scheduled for\s+(\d+\s+\w+\s+\d{4})", full)
        if next_m:
            try:
                next_release = datetime.strptime(next_m.group(1), "%d %B %Y").date().isoformat()
            except ValueError:
                pass

    # Featured occupation from page-2 narrative
    feat = _parse_featured_occupation(pages_text[1] if len(pages_text) > 1 else "")

    by_state = {code: row["ads"] for code, row in states.items() if code != "TOTAL"}
    by_major = {name: row["ads"] for name, row in majors.items()}

    now = datetime.now(timezone.utc).isoformat()
    rec = {
        "period": period or "Unknown",
        "period_iso": period_iso,
        "national_ads": nat.get("national_ads"),
        "monthly_change_pct": nat.get("monthly_change_pct"),
        "annual_change_pct": nat.get("annual_change_pct"),
        "by_state": by_state,
        "by_anzsco_major_group": by_major,
        "by_state_detail": states,
        "by_major_group_detail": majors,
        "featured_occupation": feat,
        "next_release_date": next_release,
        "source": SOURCE_NAME_FMT.format(period=period or "Latest"),
        "source_url": SOURCE_URL,
        "last_imported_at": now,
        "data_quality": DATA_QUALITY,
    }
    yield rec


def parse_summary(path: str) -> Dict[str, Any]:
    recs = list(parse_pdf(path))
    rec = recs[0] if recs else {}
    return {
        "source": rec.get("source") or "JSA Vacancy Report",
        "source_url": SOURCE_URL,
        "row_count": 1,
        "sample": [{
            "period": rec.get("period"),
            "national_ads": rec.get("national_ads"),
            "monthly_change_pct": rec.get("monthly_change_pct"),
            "annual_change_pct": rec.get("annual_change_pct"),
            "states_extracted": len(rec.get("by_state") or {}),
            "major_groups_extracted": len(rec.get("by_anzsco_major_group") or {}),
            "featured_occupation": (rec.get("featured_occupation") or {}).get("title"),
        }],
    }


# Phase 19.4c — alias so the router's PARSER_REGISTRY can call `parser.parse_workbook`
# uniformly across xlsx and pdf sources.
parse_workbook = parse_pdf
