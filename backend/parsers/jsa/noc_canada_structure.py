"""Phase 19.4 / 10.1 — Canada NOC 2021 V1.0 Classification Structure Parser."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List
from openpyxl import load_workbook

SOURCE_NAME = "StatCan NOC 2021 V1.0 Classification Structure"
SOURCE_URL = "https://www.statcan.gc.ca/en/subjects/standard/noc/2021/indexV1"


def parse_workbook(path: str) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    if p.suffix.lower() == ".csv":
        with open(p, encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("Code - NOC 2021 V1.0") or row.get("Code") or "").strip()
                if not code:
                    continue
                level_raw = row.get("Level") or "5"
                try:
                    level = int(level_raw)
                except ValueError:
                    level = 5
                yield {
                    "code": code,
                    "level": level,
                    "hierarchy_label": (row.get("Hierarchical structure") or "").strip(),
                    "title": (row.get("Class title") or row.get("Title") or "").strip(),
                    "definition": (row.get("Class definition") or row.get("Definition") or "").strip(),
                }
    else:
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active or wb[wb.sheetnames[0]]
        header = None
        for row in ws.iter_rows(values_only=True):
            if not any(row):
                continue
            if header is None:
                header = [str(c or "").strip() for c in row]
                continue
            row_dict = {k: v for k, v in zip(header, row) if k}
            code = str(row_dict.get("Code - NOC 2021 V1.0") or row_dict.get("Code") or "").strip()
            if not code or code == "None":
                continue
            level_raw = str(row_dict.get("Level") or "5").strip()
            try:
                level = int(level_raw)
            except ValueError:
                level = 5
            yield {
                "code": code,
                "level": level,
                "hierarchy_label": str(row_dict.get("Hierarchical structure") or "").strip(),
                "title": str(row_dict.get("Class title") or row_dict.get("Title") or "").strip(),
                "definition": str(row_dict.get("Class definition") or row_dict.get("Definition") or "").strip(),
            }
        wb.close()


def parse_summary(path: str) -> Dict[str, Any]:
    recs = list(parse_workbook(path))
    unit_groups = [r for r in recs if r.get("level") == 5 or len(r.get("code", "")) == 5]
    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "row_count": len(recs),
        "unit_groups_count": len(unit_groups) if unit_groups else len(recs),
        "sample": (unit_groups if unit_groups else recs)[:5],
    }
