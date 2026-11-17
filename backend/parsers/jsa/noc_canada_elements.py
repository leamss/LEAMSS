"""Phase 19.4 / 10.1 — Canada NOC 2021 V1.0 Elements Parser."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterator, List
from openpyxl import load_workbook

SOURCE_NAME = "StatCan NOC 2021 V1.0 Elements"
SOURCE_URL = "https://www.statcan.gc.ca/en/subjects/standard/noc/2021/indexV1"


def parse_workbook(path: str) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    if p.suffix.lower() == ".csv":
        with open(p, encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("Code - NOC 2021 V1.0") or row.get("Code") or "").strip()
                etype = (row.get("Element Type Label English") or row.get("Element Type") or "").strip()
                desc = (row.get("Element Description English") or row.get("Description") or "").strip()
                if not code or not etype or not desc:
                    continue
                yield {
                    "code": code,
                    "element_type": etype,
                    "description": desc,
                    "title": (row.get("Class title") or "").strip(),
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
            etype = str(row_dict.get("Element Type Label English") or row_dict.get("Element Type") or "").strip()
            desc = str(row_dict.get("Element Description English") or row_dict.get("Description") or "").strip()
            if not code or not etype or not desc or code == "None":
                continue
            yield {
                "code": code,
                "element_type": etype,
                "description": desc,
                "title": str(row_dict.get("Class title") or "").strip(),
            }
        wb.close()


def parse_summary(path: str) -> Dict[str, Any]:
    sample = []
    count = 0
    for r in parse_workbook(path):
        count += 1
        if len(sample) < 5:
            sample.append(r)
    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "row_count": count,
        "sample": sample,
    }
