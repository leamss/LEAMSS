"""Seed SkillSelect EOI Backlog data from an exported spreadsheet.

Usage:
    cd /app/backend && python /app/scripts/seed_eoi_backlog.py [path_to_xlsx_or_csv]

Defaults to /app/scripts/data/skillselect_eoi_2026-07.xlsx.
Reuses the same parser as the /api/eoi-backlog/import endpoint. Idempotent per month.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from routers.eoi_backlog import _parse_dataframe, _ensure_indexes, EOI_BACKLOG  # noqa: E402

DEFAULT = str(_HERE / "data" / "skillselect_eoi_2026-07.xlsx")


async def main(path: str):
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)
    docs = _parse_dataframe(df)
    if not docs:
        print("No valid GSM (189/190/491) rows found.")
        return
    months = sorted({d["as_at_month"] for d in docs})
    now = datetime.now(timezone.utc)
    iid = str(uuid.uuid4())
    for d in docs:
        d["import_id"] = iid
        d["imported_at"] = now
    await _ensure_indexes()
    await EOI_BACKLOG.delete_many({"as_at_month": {"$in": months}})
    for i in range(0, len(docs), 2000):
        await EOI_BACKLOG.insert_many(docs[i:i + 2000])
    total = await EOI_BACKLOG.count_documents({})
    print(f"Seeded {len(docs):,} rows for months {months}. Total in DB: {total:,}")


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    asyncio.run(main(p))
