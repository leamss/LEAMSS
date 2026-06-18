"""Phase 6.9.2 — ANZSCO / NOC Bulk Import (admin only).

Accepts CSV or Excel uploads. Two-step flow:
  1. POST /api/occupation-master/import/preview — parses + maps columns + returns
     first 10 rows + detected mapping. Nothing is written.
  2. POST /api/occupation-master/import/commit  — same payload + classification_version
     + on_duplicate strategy ('update'|'skip'). Returns full import summary.

All imported rows land as `status: 'draft'`. Admin then verifies via 6.9.3 workflow.

Column auto-mapping (case-insensitive, fuzzy keywords):
  code            ← anzsco_code, occupation_code, code, noc_code, soc_code
  title           ← occupation, title, occupation_title, name
  unit_group      ← unit_group, unit_group_code, anzsco_unit
  unit_group_name ← unit_group_name, group, occupation_group, group_name
  skill_level     ← skill_level, level
  description     ← description, summary, definition
  alt_titles      ← alternative_titles, alt_titles, also_known_as (separator: ; / | ,)
  tasks           ← typical_tasks, tasks, duties (separator: ; / | newline)
"""
import io
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/occupation-master/import", tags=["occupation-master-import"])

OCCUPATION_MASTER = db["occupation_master"]
ADMIN_ROLES = {"admin", "admin_owner"}


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


COLUMN_ALIASES = {
    "code":            ["code", "anzsco_code", "occupation_code", "noc_code", "soc_code", "ssoc", "ssoc_code"],
    "title":           ["occupation", "occupation_title", "title", "name", "occupation_name"],
    "unit_group":      ["unit_group", "unit_group_code", "anzsco_unit", "group_code"],
    "unit_group_name": ["unit_group_name", "group", "occupation_group", "group_name"],
    "minor_group":     ["minor_group", "minor_group_code"],
    "sub_major_group": ["sub_major_group", "sub_major_group_code"],
    "major_group":     ["major_group", "major_group_code"],
    "skill_level":     ["skill_level", "level"],
    "description":     ["description", "summary", "definition", "occupation_summary"],
    "alt_titles":      ["alternative_titles", "alt_titles", "also_known_as", "alternative_title"],
    "tasks":           ["typical_tasks", "tasks", "duties", "main_duties"],
    "specialisations": ["specialisations", "specializations", "specialisation"],
}


def _norm(s: str) -> str:
    return (s or "").strip().lower().replace(" ", "_").replace("-", "_")


def _detect_columns(headers: List[str]) -> Dict[str, Optional[str]]:
    """Map our canonical names → actual column name in the uploaded file."""
    norm_headers = {_norm(h): h for h in headers}
    mapping: Dict[str, Optional[str]] = {}
    for canon, aliases in COLUMN_ALIASES.items():
        found = None
        for a in aliases:
            if a in norm_headers:
                found = norm_headers[a]
                break
        mapping[canon] = found
    return mapping


def _split_list_field(value: Any) -> List[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    s = str(value).strip()
    if not s:
        return []
    for sep in [";", "|", "\n", ","]:
        if sep in s:
            return [p.strip() for p in s.split(sep) if p.strip()]
    return [s]


def _parse_upload(content: bytes, filename: str) -> pd.DataFrame:
    fn = (filename or "").lower()
    try:
        if fn.endswith(".csv"):
            return pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
        if fn.endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(content), dtype=str, keep_default_na=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}") from e
    raise HTTPException(status_code=400, detail="Unsupported file type. Use .csv, .xls, or .xlsx.")


def _row_to_doc(
    row: pd.Series,
    mapping: Dict[str, Optional[str]],
    country_code: str,
    classification_type: str,
    classification_version: str,
    user_id: str,
) -> Dict[str, Any]:
    """Convert one parsed dataframe row → occupation_master document (status=draft)."""
    def get(canon: str) -> str:
        col = mapping.get(canon)
        if not col:
            return ""
        v = row.get(col, "")
        return "" if pd.isna(v) else str(v).strip()

    code = get("code")
    title = get("title")
    skill_level_raw = get("skill_level")
    skill_level = None
    if skill_level_raw:
        try:
            skill_level = int(float(skill_level_raw))
        except ValueError:
            skill_level = None
    now = datetime.now(timezone.utc)
    return {
        "occupation_id": str(uuid.uuid4()),
        "code": code,
        "classification_type": classification_type,
        "classification_version": classification_version,
        "country_code": country_code.upper(),
        "title": title,
        "alternative_titles": _split_list_field(row.get(mapping["alt_titles"], "") if mapping["alt_titles"] else ""),
        "specialisations": _split_list_field(row.get(mapping["specialisations"], "") if mapping["specialisations"] else ""),
        "hierarchy": {
            "major_group": get("major_group"),
            "sub_major_group": get("sub_major_group"),
            "minor_group": get("minor_group"),
            "unit_group": get("unit_group"),
            "unit_group_name": get("unit_group_name"),
        },
        "description": get("description"),
        "typical_tasks": _split_list_field(row.get(mapping["tasks"], "") if mapping["tasks"] else ""),
        "skill_level": skill_level,
        "assessing_authority": {"body_id": None, "name": "", "full_name": "", "website": ""},
        "skill_assessment_details": {
            "requirements": "", "criteria_notes": "", "qualification_rules": "",
            "documents_required": [], "fee_native": None, "fee_currency": None, "processing_time": "",
        },
        "visa_pathways": {"pathway_lists": [], "visa_eligibility": [], "processing_times": {}},
        "state_territory_eligibility": [],
        "similar_codes": [],
        "status": "draft",
        "verification": {
            "verified_by": None, "verified_at": None,
            "source_reference": f"Bulk import · {classification_version}", "review_notes": "",
        },
        "ai_draft": {
            "description": "", "typical_tasks": [],
            "generated_at": None, "generated_by_model": None, "is_stale": False,
        },
        "linked_product_id": None,
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
        "last_reviewed_at": None,
        "_import_classification_version": classification_version,
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/occupation-master/import/preview
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/preview")
async def preview_import(
    file: UploadFile = File(...),
    country_code: str = Form(...),
    classification_type: str = Form("ANZSCO"),
    current_user: dict = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    df = _parse_upload(content, file.filename or "")
    if df.empty:
        raise HTTPException(status_code=400, detail="File has 0 data rows")

    headers = list(df.columns)
    mapping = _detect_columns(headers)
    if not mapping.get("code") or not mapping.get("title"):
        return {
            "ok": False,
            "headers": headers,
            "detected_mapping": mapping,
            "error": "Could not auto-detect required 'code' and 'title' columns. Rename columns and retry.",
            "total_rows": len(df),
        }

    # First 10 sample rows (normalised)
    sample = []
    fake_user = "preview"
    for _, r in df.head(10).iterrows():
        sample.append(_row_to_doc(r, mapping, country_code, classification_type,
                                   "PREVIEW · not committed", fake_user))

    # Detect potential duplicates against existing occupation_master
    codes_in_file = set()
    duplicates_in_file = []
    for _, r in df.iterrows():
        c = str(r.get(mapping["code"], "")).strip()
        if not c:
            continue
        if c in codes_in_file:
            duplicates_in_file.append(c)
        codes_in_file.add(c)
    existing_codes = set()
    async for d in OCCUPATION_MASTER.find(
        {"country_code": country_code.upper(), "code": {"$in": list(codes_in_file)}},
        {"_id": 0, "code": 1},
    ):
        existing_codes.add(d["code"])

    # Phase 19.6 — issue short-lived preview token (required by /commit)
    from services.preview_token_service import issue_preview_token, TOKEN_LIFETIME_SECONDS
    token = issue_preview_token(content)
    return {
        "ok": True,
        "headers": headers,
        "detected_mapping": mapping,
        "total_rows": len(df),
        "rows_with_code": len(codes_in_file),
        "duplicates_in_file": duplicates_in_file[:20],
        "duplicates_in_db": sorted(existing_codes)[:20],
        "duplicates_in_db_count": len(existing_codes),
        "sample_rows": sample,
        "preview_token": token,
        "preview_token_expires_in_seconds": TOKEN_LIFETIME_SECONDS,
    }


class CommitRequest(BaseModel):
    classification_version: str
    on_duplicate: str = "skip"  # 'skip' | 'update'


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/occupation-master/import/commit
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/commit")
async def commit_import(
    file: UploadFile = File(...),
    country_code: str = Form(...),
    classification_type: str = Form("ANZSCO"),
    classification_version: str = Form(...),
    on_duplicate: str = Form("skip"),
    preview_token: str = Form(""),  # Phase 19.6 — required by /commit
    current_user: dict = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    if on_duplicate not in ("skip", "update"):
        raise HTTPException(status_code=400, detail="on_duplicate must be 'skip' or 'update'")
    # Phase 19.6 — preview_token enforcement
    from services.preview_token_service import verify_preview_token
    if not preview_token:
        raise HTTPException(
            status_code=400,
            detail="preview_token required — call /api/occupation-master/import/preview first to get an authorised token.",
        )
    content = await file.read()
    if not verify_preview_token(preview_token, content):
        raise HTTPException(
            status_code=400,
            detail="invalid or expired preview_token — re-preview the exact same file.",
        )

    df = _parse_upload(content, file.filename or "")
    if df.empty:
        raise HTTPException(status_code=400, detail="File has 0 data rows")
    mapping = _detect_columns(list(df.columns))
    if not mapping.get("code") or not mapping.get("title"):
        raise HTTPException(status_code=400, detail="Required 'code' and 'title' columns not detected")

    # Phase 19.6 — open import batch
    from services import import_batch_service as ibs
    from core.database import db as _db
    batch = await ibs.open_batch(
        _db,
        ingestion_path="phase_6.9.2_bulk",
        endpoint="POST /api/occupation-master/import/commit",
        uploaded_by=current_user.get("id") or current_user.get("email", ""),
        uploaded_by_name=current_user.get("name") or current_user.get("email", "admin"),
        file_name=file.filename or "upload.xlsx",
        file_hash=ibs.file_sha256(content),
        file_size_bytes=len(content),
        target_collection="occupation_master",
    )

    imported = 0
    updated = 0
    skipped = 0
    errors: List[str] = []
    seen_codes_in_file: set = set()

    for idx, row in df.iterrows():
        try:
            code = str(row.get(mapping["code"], "")).strip()
            if not code:
                errors.append(f"Row {idx + 2}: missing code, skipped")
                skipped += 1
                ibs.record_skip(batch, {"row": idx + 2}, "missing code")
                continue
            if code in seen_codes_in_file:
                errors.append(f"Row {idx + 2}: duplicate code '{code}' within file, skipped")
                skipped += 1
                ibs.record_skip(batch, {"country_code": country_code.upper(), "code": code}, "duplicate in file")
                continue
            seen_codes_in_file.add(code)

            existing = await OCCUPATION_MASTER.find_one(
                {"country_code": country_code.upper(), "code": code}, {"_id": 0}
            )
            if existing:
                if on_duplicate == "skip":
                    skipped += 1
                    ibs.record_skip(batch, {"country_code": country_code.upper(), "code": code}, "exists, on_duplicate=skip")
                    continue
                # update: refresh select fields, preserve verification + linked_product_id + occupation_id
                new_doc = _row_to_doc(row, mapping, country_code, classification_type,
                                       classification_version, current_user["id"])
                preserve = {
                    "occupation_id": existing.get("occupation_id"),
                    "verification": existing.get("verification"),
                    "linked_product_id": existing.get("linked_product_id"),
                    "ai_draft": existing.get("ai_draft"),
                    "created_at": existing.get("created_at"),
                    "created_by": existing.get("created_by"),
                    "status": existing.get("status"),  # keep verified records verified
                    # Preserve curated fields that bulk import doesn't carry:
                    # assessing authority, visa pathway eligibility, state demand.
                    "assessing_authority": existing.get("assessing_authority") or {},
                    "skill_assessment_details": existing.get("skill_assessment_details") or {},
                    "visa_pathways": existing.get("visa_pathways") or {},
                    "state_territory_eligibility": existing.get("state_territory_eligibility") or [],
                }
                new_doc.update(preserve)
                new_doc["updated_at"] = datetime.now(timezone.utc)
                new_doc["_re_imported_at"] = new_doc["updated_at"]
                await OCCUPATION_MASTER.update_one({"occupation_id": preserve["occupation_id"]}, {"$set": new_doc})
                ibs.record_update(batch, preserve["occupation_id"],
                                  {"country_code": country_code.upper(), "code": code}, existing)
                updated += 1
                continue

            doc = _row_to_doc(row, mapping, country_code, classification_type,
                               classification_version, current_user["id"])
            await OCCUPATION_MASTER.insert_one(doc)
            ibs.record_create(batch, doc["occupation_id"],
                              {"country_code": country_code.upper(), "code": code})
            imported += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"Row {idx + 2}: {e}")
            skipped += 1
            ibs.record_skip(batch, {"row": idx + 2}, str(e)[:120])

    # Close batch + audit log
    await ibs.close_batch(_db, batch, total_rows=len(df))
    await _db["audit_logs"].insert_one({
        "id": str(uuid.uuid4()),
        "action": "occupation_master.bulk_import",
        "user_id": current_user.get("id") or current_user.get("email"),
        "at": datetime.now(timezone.utc),
        "summary": {
            "batch_id": batch["batch_id"],
            "ingestion_path": "phase_6.9.2_bulk",
            "file_name": file.filename,
            "imported": imported, "updated": updated, "skipped": skipped,
            "total_rows": len(df),
        },
    })

    return {
        "ok": True,
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:50],
        "total_processed": imported + updated + skipped,
        "classification_version": classification_version,
        "batch_id": batch["batch_id"],
    }
