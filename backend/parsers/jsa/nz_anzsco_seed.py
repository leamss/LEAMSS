"""Phase 19.4 / 12.1 — New Zealand ANZSCO / Green List / AEWV Parser."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterator, List
from openpyxl import load_workbook
from core.scrapers.nz_anzsco_seed import NZ_OCCUPATIONS

SOURCE_NAME = "Immigration New Zealand ANZSCO 1.3 / Green List"
SOURCE_URL = "https://www.immigration.govt.nz/work/requirements-for-work-visas/green-list-occupations-qualifications-and-skills/"


def parse_workbook(path: str) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    records = []
    if p.suffix.lower() == ".csv":
        try:
            with open(p, encoding="utf-8-sig", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = (row.get("ANZSCO Code") or row.get("code") or row.get("Code") or "").strip()
                    title = (row.get("Occupation Title") or row.get("title") or row.get("Title") or "").strip()
                    skill = (row.get("Skill Level") or row.get("skill_level") or "1").strip()
                    if code and title:
                        records.append({
                            "country_code": "NZ",
                            "code": code,
                            "title": title,
                            "skill_level": int(skill) if skill.isdigit() else 1,
                        })
        except Exception:
            pass
    elif p.suffix.lower() in (".xlsx", ".xls"):
        try:
            wb = load_workbook(path, read_only=True, data_only=True)
            sheet_name = "Table 5" if "Table 5" in wb.sheetnames else wb.sheetnames[0]
            ws = wb[sheet_name]
            for row in ws.iter_rows(values_only=True):
                for i, c in enumerate(row):
                    s = str(c or "").strip()
                    if len(s) == 6 and s.isdigit():
                        title = str(row[i + 1] or "").strip() if i + 1 < len(row) else ""
                        if title:
                            records.append({
                                "country_code": "NZ",
                                "code": s,
                                "title": title,
                                "skill_level": 1,
                            })
            wb.close()
        except Exception:
            pass

    if not records:
        for code, title, skill_level, group in NZ_OCCUPATIONS:
            records.append({
                "country_code": "NZ",
                "code": code,
                "title": title,
                "skill_level": skill_level,
                "unit_group_name": group,
            })

    for r in records:
        yield r


def parse_summary(path: str) -> Dict[str, Any]:
    recs = list(parse_workbook(path))
    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "row_count": len(recs),
        "sample": recs[:5],
    }
