"""SkillSelect EOI Backlog data — import + lookup.

The official DHA SkillSelect EOI dashboard (hSKLS02) has no public API/CSV; it is a
Qlik BI app with monthly refresh and privacy suppression (counts < 20 shown as "<20").
Consultants export the "Selections made / EOI data" spreadsheet from the dashboard and
upload it here. We store it in `eoi_backlog` keyed by occupation code + visa subclass +
EOI status + points, and surface the SUBMITTED (pool) backlog per occupation in the
client Assessment Report.

AU-only (SkillSelect is Australia). Matched to occupation_master by 6-digit ANZSCO code.
"""
from __future__ import annotations

import io
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/eoi-backlog", tags=["eoi-backlog"])

EOI_BACKLOG = db["eoi_backlog"]
ADMIN_ROLES = {"admin", "admin_owner"}

# GSM (occupation-based) subclasses we surface in reports
SUPPORTED_SUBCLASSES = {"189", "190", "491"}

_VISA_RE = re.compile(r"^\s*(\d{3})([A-Za-z]+)?\s*(.*)$")
_OCC_RE = re.compile(r"^\s*(\d{6})\s+(.*)$")


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _norm_col(c: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(c).strip().lower())


def _match_columns(cols: List[str]) -> Dict[str, str]:
    """Map spreadsheet headers -> canonical keys."""
    aliases = {
        "as_at_month": ["asatmonth", "month", "asat"],
        "visa_type": ["visatype", "visa", "visasubclass", "subclass"],
        "occupation": ["occupation", "anzsco", "occupationcode"],
        "eoi_status": ["eoistatus", "status"],
        "points": ["points", "point", "pointscore"],
        "count": ["counteois", "count", "counteoi", "eois", "numberofeois"],
    }
    norm_map = {_norm_col(c): c for c in cols}
    out: Dict[str, str] = {}
    for key, al in aliases.items():
        for a in al:
            if a in norm_map:
                out[key] = norm_map[a]
                break
    return out


def _parse_month(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y", "%b %Y", "%B %Y"):
        try:
            return datetime.strptime(s[:19], fmt).date().isoformat()
        except ValueError:
            continue
    try:
        return pd.to_datetime(s).date().isoformat()
    except Exception:
        return s[:10] or None


def _parse_count(val: Any) -> Dict[str, Any]:
    s = str(val).strip() if val is not None else ""
    if s in ("", "nan", "None"):
        return {"count": 0, "count_raw": "0", "suppressed": False}
    if "<" in s or s.lower() in ("<20", "suppressed"):
        return {"count": None, "count_raw": "<20", "suppressed": True}
    try:
        n = int(float(s.replace(",", "")))
        return {"count": n, "count_raw": str(n), "suppressed": False}
    except ValueError:
        return {"count": None, "count_raw": s, "suppressed": True}


def _parse_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    cols = _match_columns(list(df.columns))
    required = {"visa_type", "occupation", "eoi_status", "points", "count"}
    missing = required - set(cols.keys())
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing expected columns: {sorted(missing)}. Found headers: {list(df.columns)}",
        )

    docs: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        visa_raw = str(r[cols["visa_type"]]).strip()
        vm = _VISA_RE.match(visa_raw)
        if not vm:
            continue
        subclass = vm.group(1)
        if subclass not in SUPPORTED_SUBCLASSES:
            continue

        occ_raw = str(r[cols["occupation"]]).strip()
        om = _OCC_RE.match(occ_raw)
        if not om:
            continue  # skip N/A occupation rows
        occ_code = om.group(1)
        occ_title = om.group(2).strip()

        pts_raw = r[cols["points"]]
        try:
            points = int(float(str(pts_raw)))
        except (ValueError, TypeError):
            continue  # skip N/A points

        cnt = _parse_count(r[cols["count"]])
        month = _parse_month(r[cols["as_at_month"]]) if "as_at_month" in cols else None
        stream_code = (vm.group(2) or "").upper()
        stream_label = (vm.group(3) or "").strip()

        docs.append({
            "as_at_month": month or "unknown",
            "visa_subclass": subclass,
            "visa_stream_code": stream_code,
            "visa_stream": stream_label,
            "occupation_code": occ_code,
            "occupation_title": occ_title,
            "eoi_status": str(r[cols["eoi_status"]]).strip().upper(),
            "points": points,
            "count": cnt["count"],
            "count_raw": cnt["count_raw"],
            "suppressed": cnt["suppressed"],
        })
    return docs


async def _ensure_indexes():
    await EOI_BACKLOG.create_index(
        [("occupation_code", 1), ("visa_subclass", 1), ("eoi_status", 1), ("points", -1)]
    )
    await EOI_BACKLOG.create_index([("as_at_month", -1)])


# ════════════════════════════════════════════════════════════════
# Report lookup helper (imported by assessment_reports)
# ════════════════════════════════════════════════════════════════
def _client_bracket(points: Optional[int]) -> Optional[int]:
    if points is None:
        return None
    return int(points) // 5 * 5


async def build_eoi_for_occupation(
    occupation_code: str, client_points: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Return SUBMITTED (pool) EOI backlog for an occupation, grouped by subclass & points.

    491 combines the SNR + FSR streams. Suppressed cells ("<20") stay flagged.
    """
    if not occupation_code:
        return None
    latest = await EOI_BACKLOG.find_one({}, {"as_at_month": 1}, sort=[("as_at_month", -1)])
    if not latest:
        return None
    month = latest.get("as_at_month")

    cursor = EOI_BACKLOG.find({
        "as_at_month": month,
        "occupation_code": occupation_code,
        "eoi_status": "SUBMITTED",
    }, {"_id": 0})
    docs = await cursor.to_list(length=10000)
    if not docs:
        return None

    title = None
    agg: Dict[str, Dict[int, Dict[str, Any]]] = {}
    for d in docs:
        title = title or d.get("occupation_title")
        sc = d.get("visa_subclass")
        pts = d.get("points")
        if pts is None or sc not in SUPPORTED_SUBCLASSES:
            continue
        cell = agg.setdefault(sc, {}).setdefault(pts, {"count": 0, "has_numeric": False, "suppressed": False})
        if d.get("count") is not None:
            cell["count"] += d["count"]
            cell["has_numeric"] = True
        if d.get("suppressed"):
            cell["suppressed"] = True

    c_bracket = _client_bracket(client_points)
    subclasses_out: List[Dict[str, Any]] = []
    for sc in ("189", "190", "491"):
        if sc not in agg:
            continue
        rows = []
        total = 0
        total_has_suppressed = False
        ahead = 0
        ahead_has_suppressed = False
        for pts in sorted(agg[sc].keys(), reverse=True):
            cell = agg[sc][pts]
            if cell["has_numeric"]:
                cnt, raw = cell["count"], str(cell["count"])
                total += cell["count"]
            elif cell["suppressed"]:
                cnt, raw = None, "<20"
                total_has_suppressed = True
            else:
                cnt, raw = 0, "0"
            if c_bracket is not None and pts >= c_bracket:
                if cell["has_numeric"]:
                    ahead += cell["count"]
                elif cell["suppressed"]:
                    ahead_has_suppressed = True
            rows.append({
                "points": pts,
                "count": cnt,
                "raw": raw,
                "is_client_bracket": c_bracket is not None and pts == c_bracket,
            })
        subclasses_out.append({
            "subclass": sc,
            "rows": rows,
            "total": total,
            "total_suppressed": total_has_suppressed,
            "ahead_of_client": ahead,
            "ahead_suppressed": ahead_has_suppressed,
        })

    if not subclasses_out:
        return None

    # Build a unified table (points rows × subclass columns) for the report.
    present_sc = [s["subclass"] for s in subclasses_out]
    all_points = set()
    for s in subclasses_out:
        for row in s["rows"]:
            all_points.add(row["points"])
    # Meaningful competition range for GSM is 65+; always keep the client's bracket.
    keep_points = sorted(
        [p for p in all_points if p >= 65 or (c_bracket is not None and p == c_bracket)],
        reverse=True,
    )
    sc_row_map = {s["subclass"]: {r["points"]: r for r in s["rows"]} for s in subclasses_out}
    unified_rows = []
    for p in keep_points:
        cells = {}
        for sc in present_sc:
            r = sc_row_map[sc].get(p)
            cells[sc] = {"raw": r["raw"], "count": r["count"]} if r else {"raw": "—", "count": 0}
        unified_rows.append({
            "points": p,
            "is_client_bracket": c_bracket is not None and p == c_bracket,
            "cells": cells,
        })

    return {
        "as_at_month": month,
        "occupation_code": occupation_code,
        "occupation_title": title,
        "client_points": client_points,
        "client_bracket": c_bracket,
        "subclasses": subclasses_out,
        "unified": {"subclasses": present_sc, "rows": unified_rows},
    }


async def eoi_pool_total(occupation_code: str, subclass: str = "189") -> Optional[Dict[str, Any]]:
    """Compact SUBMITTED total for one subclass (used in occupation comparison)."""
    latest = await EOI_BACKLOG.find_one({}, {"as_at_month": 1}, sort=[("as_at_month", -1)])
    if not latest:
        return None
    month = latest.get("as_at_month")
    docs = await EOI_BACKLOG.find({
        "as_at_month": month, "occupation_code": occupation_code,
        "visa_subclass": subclass, "eoi_status": "SUBMITTED",
    }, {"_id": 0, "count": 1, "suppressed": 1}).to_list(5000)
    if not docs:
        return None
    total = sum(d["count"] for d in docs if d.get("count") is not None)
    suppressed = any(d.get("suppressed") for d in docs)
    return {"subclass": subclass, "total": total, "suppressed": suppressed, "as_at_month": month}


# ════════════════════════════════════════════════════════════════
# Admin endpoints
# ════════════════════════════════════════════════════════════════
@router.post("/import")
async def import_eoi(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    raw = await file.read()
    name = (file.filename or "").lower()
    try:
        if name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(raw))
        else:
            df = pd.read_excel(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    docs = _parse_dataframe(df)
    if not docs:
        raise HTTPException(status_code=400, detail="No valid GSM (189/190/491) occupation rows found in file")

    months = sorted({d["as_at_month"] for d in docs})
    import_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    for d in docs:
        d["import_id"] = import_id
        d["imported_at"] = now

    await _ensure_indexes()
    # Replace existing data for the months present in this file (idempotent re-import)
    await EOI_BACKLOG.delete_many({"as_at_month": {"$in": months}})
    # Insert in chunks
    for i in range(0, len(docs), 2000):
        await EOI_BACKLOG.insert_many(docs[i:i + 2000])

    distinct_occ = len({d["occupation_code"] for d in docs})
    submitted = sum(1 for d in docs if d["eoi_status"] == "SUBMITTED")
    return {
        "ok": True,
        "import_id": import_id,
        "rows_imported": len(docs),
        "months": months,
        "distinct_occupations": distinct_occ,
        "submitted_rows": submitted,
    }


@router.get("/status")
async def eoi_status(current_user: dict = Depends(get_current_user)):
    total = await EOI_BACKLOG.count_documents({})
    if total == 0:
        return {"has_data": False, "total_rows": 0}
    latest = await EOI_BACKLOG.find_one({}, {"as_at_month": 1, "imported_at": 1}, sort=[("as_at_month", -1)])
    month = latest.get("as_at_month")
    month_rows = await EOI_BACKLOG.count_documents({"as_at_month": month})
    distinct_occ = len(await EOI_BACKLOG.distinct("occupation_code", {"as_at_month": month}))
    by_subclass = {}
    for sc in ("189", "190", "491"):
        by_subclass[sc] = await EOI_BACKLOG.count_documents(
            {"as_at_month": month, "visa_subclass": sc, "eoi_status": "SUBMITTED"}
        )
    all_months = sorted(await EOI_BACKLOG.distinct("as_at_month"), reverse=True)
    return {
        "has_data": True,
        "total_rows": total,
        "latest_month": month,
        "latest_month_rows": month_rows,
        "distinct_occupations": distinct_occ,
        "submitted_rows_by_subclass": by_subclass,
        "all_months": all_months,
        "imported_at": latest.get("imported_at"),
    }


@router.get("/occupation/{code}")
async def eoi_for_occupation(
    code: str,
    client_points: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    data = await build_eoi_for_occupation(code, client_points)
    if not data:
        raise HTTPException(status_code=404, detail="No EOI backlog data for this occupation")
    return data
