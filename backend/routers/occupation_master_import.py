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

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
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


SEO_COLUMN_ALIASES = {
    "code": ["code", "anzsco_code", "occupation_code", "noc_code", "page_code", "anzsco", "code_number"],
    "country_code": ["country", "country_code", "country_iso", "jurisdiction", "nation"],
    "title": ["occupation_title", "title", "occupation", "name", "occupation_name"],
    "page_url": ["page_url", "page_path", "url", "path", "page", "atlas_url"],
    "meta_title": ["meta_title", "page_title", "seo_title", "title_tag", "meta_title_tag", "serp_title"],
    "meta_description": ["meta_description", "meta_desc", "seo_description", "description_tag", "meta_description_tag", "serp_description"],
    "keywords": ["keywords", "meta_keywords", "seo_keywords", "focus_keywords", "search_keywords"],
    "focus_keyword": ["focus_keyword", "focus_kw", "primary_keyword", "target_keyword", "keyword"],
    "canonical_url": ["canonical_url", "canonical", "canonical_link"],
    "og_title": ["og_title", "open_graph_title", "social_title"],
    "og_description": ["og_description", "open_graph_description", "social_description"],
    "og_image": ["og_image", "open_graph_image", "social_image", "og_image_url"],
    "twitter_title": ["twitter_title", "x_title", "twitter_card_title"],
    "twitter_description": ["twitter_description", "x_description", "twitter_card_description"],
    "twitter_image": ["twitter_image", "x_image", "twitter_card_image"],
    "meta_robots": ["meta_robots", "robots", "robots_tag", "indexing"],
    "schema_type": ["schema_type", "schema", "structured_data_type"],
}


def _detect_seo_columns(headers: List[str]) -> Dict[str, Optional[str]]:
    """Map our canonical SEO field names → actual column name in the uploaded file."""
    norm_headers = {_norm(h): h for h in headers}
    mapping: Dict[str, Optional[str]] = {}
    for canon, aliases in SEO_COLUMN_ALIASES.items():
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


# ─────────────────────────────────────────────────────────────────────────────
# Phase 19.8 — Bulk SEO Attributes Excel Upload & Template Engine
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/seo/template")
async def download_seo_excel_template(
    country: str = Query("AU", description="AU | CA | NZ | ALL"),
    mode: str = Query("template", description="template | export"),
    current_user: dict = Depends(get_current_user),
):
    """Download SEO attributes Excel template or current data export pre-filled.
    Includes all SERP, Social Graph (OG/Twitter), Canonical and Schema tags.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin permissions required for SEO bulk operations")

    country_clean = (country or "AU").strip().upper()
    mode_clean = (mode or "template").strip().lower()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"SEO_Attributes_{country_clean}"

    headers = [
        "Country", "Code", "Occupation_Title", "Page_URL",
        "Meta_Title", "Meta_Description", "Keywords", "Focus_Keyword",
        "Canonical_URL", "OG_Title", "OG_Description", "OG_Image_URL",
        "Twitter_Title", "Twitter_Description", "Meta_Robots", "Schema_Type"
    ]

    header_fill = PatternFill(start_color="1F4D44", end_color="1F4D44", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="E0E0E0"),
        right=Side(style="thin", color="E0E0E0"),
        top=Side(style="thin", color="E0E0E0"),
        bottom=Side(style="thin", color="E0E0E0"),
    )

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    ws.row_dimensions[1].height = 28

    if mode_clean == "export":
        # Pre-fill with actual occupations from MongoDB
        query: Dict[str, Any] = {"status": {"$ne": "superseded"}}
        if country_clean != "ALL":
            query["country_code"] = country_clean

        cursor = OCCUPATION_MASTER.find(
            query,
            {
                "_id": 0, "code": 1, "title": 1, "country_code": 1,
                "seo_meta": 1,
            }
        ).sort("code", 1)

        row_idx = 2
        async for doc in cursor:
            cc = (doc.get("country_code") or "AU").upper()
            code = str(doc.get("code") or "").strip()
            title = doc.get("title") or "Occupation"
            seo = doc.get("seo_meta") or {}

            meta_title = (
                seo.get("meta_title") or seo.get("page_title") or
                f"{title} ({code}) — {cc} Migration Guide | LEAMSS"
            )
            meta_desc = (
                seo.get("meta_description") or
                f"Complete migration guide for {title} ({code}) in {cc}. Check visa cutoffs, assessing body criteria, and points eligibility."
            )
            keywords = seo.get("keywords") or f"{title}, {code}, {cc} PR, immigration"
            focus_kw = seo.get("focus_keyword") or f"{title} {cc} PR"
            canonical = seo.get("canonical_url") or f"https://leamss.com/atlas/{cc.lower()}/{code}"
            og_title = seo.get("og_title") or meta_title
            og_desc = seo.get("og_description") or meta_desc
            og_img = seo.get("og_image") or "https://leamss.com/leamss-logo.png"
            tw_title = seo.get("twitter_title") or og_title
            tw_desc = seo.get("twitter_description") or og_desc
            robots = seo.get("meta_robots") or "index, follow, max-image-preview:large, max-snippet:-1"
            schema = seo.get("schema_type") or "Occupation"

            row_data = [
                cc, code, title, f"/atlas/{cc.lower()}/{code}",
                meta_title, meta_desc, keywords, focus_kw,
                canonical, og_title, og_desc, og_img,
                tw_title, tw_desc, robots, schema
            ]

            for c_idx, val in enumerate(row_data, 1):
                c = ws.cell(row=row_idx, column=c_idx, value=val)
                c.border = thin_border
                c.alignment = Alignment(vertical="center")
            row_idx += 1
    else:
        # Template mode: add 3 illustrative sample rows
        samples = [
            [
                "AU", "261313", "Software Engineer", "/atlas/au/261313",
                "Software Engineer (261313) — Australia ANZSCO Migration Guide | LEAMSS",
                "Complete migration guide for Software Engineer (ANZSCO 261313) in Australia. Check DHA invitation round cutoffs, ACS skill assessment criteria, and 189/190/491 visa pathways.",
                "Software Engineer, 261313, Australia PR, ACS skill assessment, MLTSSL",
                "Software Engineer Australia PR",
                "https://leamss.com/atlas/au/261313",
                "Software Engineer — Australia Migration Pathway",
                "Explore 189/190/491 visa invitation cutoffs, ACS assessment requirements, and salary trends for Software Engineer.",
                "https://leamss.com/leamss-logo.png",
                "Software Engineer — Australia Migration Pathway",
                "Explore 189/190/491 visa invitation cutoffs, ACS assessment requirements, and salary trends for Software Engineer.",
                "index, follow, max-image-preview:large, max-snippet:-1",
                "Occupation"
            ],
            [
                "CA", "21231", "Software Engineers and Designers", "/atlas/ca/21231",
                "Software Engineers (NOC 21231) — Canada Express Entry & PNP Guide | LEAMSS",
                "Migrate to Canada as a Software Engineer (NOC 21231, TEER 1). Check Express Entry STEM category draws, WES ECA credentials, and provincial nominee streams in Ontario and BC.",
                "Software Engineer, NOC 21231, Canada Express Entry, STEM Category Draw, WES ECA",
                "Software Engineer Canada PR",
                "https://leamss.com/atlas/ca/21231",
                "Software Engineer — Canada Migration Pathway",
                "Check Canada Express Entry STEM draws, WES ECA requirements, and provincial nomination options for NOC 21231.",
                "https://leamss.com/leamss-logo.png",
                "Software Engineer — Canada Migration Pathway",
                "Check Canada Express Entry STEM draws, WES ECA requirements, and provincial nomination options for NOC 21231.",
                "index, follow, max-image-preview:large, max-snippet:-1",
                "Occupation"
            ],
            [
                "NZ", "261313", "Software Engineer", "/atlas/nz/261313",
                "Software Engineer (261313) — New Zealand Green List & SMC Residence | LEAMSS",
                "Migrate to New Zealand as Software Engineer. Check Green List Tier 1 Straight to Residence requirements, NZQA qualification recognition, and AEWV accredited employer rules.",
                "Software Engineer, New Zealand Green List Tier 1, Straight to Residence, SMC, NZQA",
                "Software Engineer New Zealand Residence",
                "https://leamss.com/atlas/nz/261313",
                "Software Engineer — New Zealand Green List Pathway",
                "Direct Straight to Residence pathway for Software Engineer under INZ Green List Tier 1.",
                "https://leamss.com/leamss-logo.png",
                "Software Engineer — New Zealand Green List Pathway",
                "Direct Straight to Residence pathway for Software Engineer under INZ Green List Tier 1.",
                "index, follow, max-image-preview:large, max-snippet:-1",
                "Occupation"
            ]
        ]
        for r_idx, s in enumerate(samples, 2):
            for c_idx, val in enumerate(s, 1):
                c = ws.cell(row=r_idx, column=c_idx, value=val)
                c.border = thin_border
                c.alignment = Alignment(vertical="center")

    # Set column widths
    col_widths = {
        "A": 10, "B": 12, "C": 28, "D": 22,
        "E": 45, "F": 55, "G": 35, "H": 25,
        "I": 35, "J": 35, "K": 45, "L": 30,
        "M": 35, "N": 45, "O": 25, "P": 16,
    }
    for col_l, width in col_widths.items():
        ws.column_dimensions[col_l].width = width

    # Sheet 2: Guidelines
    ws_guide = wb.create_sheet(title="Instructions_&_Guidelines")
    guide_headers = ["Field Name", "Character Limit / Format", "Description & Google Best Practices"]
    for c_idx, gh in enumerate(guide_headers, 1):
        c = ws_guide.cell(row=1, column=c_idx, value=gh)
        c.fill = PatternFill(start_color="1F4D44", end_color="1F4D44", fill_type="solid")
        c.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        c.alignment = Alignment(horizontal="center", vertical="center")

    guidelines = [
        ("Country", "AU / CA / NZ", "Country jurisdiction code. Determines whether page is rendered under /atlas/au, /ca, or /nz."),
        ("Code", "ANZSCO or NOC code", "Mandatory unique occupation code. Used to match and update the exact public page."),
        ("Occupation_Title", "Standard title", "For reference and verification. Keeps export organized."),
        ("Page_URL", "/atlas/{country}/{code}", "Live relative public page URL path."),
        ("Meta_Title", "50–60 characters", "Displayed on browser tabs and Google Search result title link. Include Occupation and Country."),
        ("Meta_Description", "140–160 characters", "Google Search snippet summary. Entices clicks with visa cutoffs, requirements and free assessment."),
        ("Keywords", "Comma-separated", "Focus keywords and variations for indexing and internal tagging."),
        ("Focus_Keyword", "1–4 words", "Primary target search term for SEO audit scoring."),
        ("Canonical_URL", "Full HTTPS link", "Self-referencing canonical tag to prevent duplicate content penalties."),
        ("OG_Title", "40–70 characters", "Title displayed when link is shared on WhatsApp, LinkedIn, Twitter/X, Facebook."),
        ("OG_Description", "100–160 characters", "Description displayed in social media rich link preview cards."),
        ("OG_Image_URL", "HTTPS image URL", "1200x630px social banner. Defaults to official LEAMSS logo banner."),
        ("Twitter_Title", "40–70 characters", "Twitter summary card title."),
        ("Twitter_Description", "100–160 characters", "Twitter card snippet description."),
        ("Meta_Robots", "index, follow ...", "Standard: 'index, follow, max-image-preview:large, max-snippet:-1'. Use 'noindex' only to hide draft."),
        ("Schema_Type", "Occupation | Article | Course", "Google structured data schema.org entity type. Default is 'Occupation'."),
    ]

    for g_idx, (fname, flim, fdesc) in enumerate(guidelines, 2):
        ws_guide.cell(row=g_idx, column=1, value=fname).font = Font(bold=True)
        ws_guide.cell(row=g_idx, column=2, value=flim).font = Font(color="0E5C5C", italic=True)
        ws_guide.cell(row=g_idx, column=3, value=fdesc)

    ws_guide.column_dimensions["A"].width = 22
    ws_guide.column_dimensions["B"].width = 28
    ws_guide.column_dimensions["C"].width = 75

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"LEAMSS_SEO_Attributes_{country_clean}_{mode_clean}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/seo/preview")
async def preview_seo_excel_upload(
    file: UploadFile = File(...),
    country_code: str = Form("AU"),
    current_user: dict = Depends(get_current_user),
):
    """Preview SEO attributes Excel / CSV upload before committing.
    Matches codes in database, reports matched vs missing, and shows diffs.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin permissions required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    df = _parse_upload(content, file.filename)
    mapping = _detect_seo_columns(df.columns.tolist())

    if not mapping.get("code"):
        raise HTTPException(
            status_code=400,
            detail="Could not detect occupation 'Code' column in file. Expected 'Code', 'ANZSCO_Code', or 'NOC_Code'."
        )

    default_cc = (country_code or "AU").strip().upper()
    total_rows = len(df)
    matched_count = 0
    not_found_count = 0
    not_found_codes: List[str] = []
    sample_rows: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        raw_code = str(row.get(mapping["code"]) or "").strip()
        if not raw_code or raw_code == "nan":
            continue

        raw_cc = str(row.get(mapping.get("country_code")) or "").strip().upper() if mapping.get("country_code") else ""
        if not raw_cc or raw_cc == "NAN":
            raw_cc = default_cc

        # If code contains country prefix like AU-261313, strip prefix
        code = raw_code
        if "-" in raw_code:
            parts = raw_code.split("-", 1)
            if parts[0].upper() in ("AU", "CA", "NZ"):
                raw_cc = parts[0].upper()
                code = parts[1].strip()

        # Clean code of floating point notation (e.g. '261313.0')
        if code.endswith(".0"):
            code = code[:-2]

        existing = await OCCUPATION_MASTER.find_one(
            {"country_code": raw_cc, "code": code, "status": {"$ne": "superseded"}},
            {"_id": 0, "title": 1, "code": 1, "country_code": 1, "seo_meta": 1}
        )

        new_meta_title = str(row.get(mapping.get("meta_title")) or "").strip() if mapping.get("meta_title") else ""
        new_meta_desc = str(row.get(mapping.get("meta_description")) or "").strip() if mapping.get("meta_description") else ""
        new_keywords = str(row.get(mapping.get("keywords")) or "").strip() if mapping.get("keywords") else ""
        new_focus_kw = str(row.get(mapping.get("focus_keyword")) or "").strip() if mapping.get("focus_keyword") else ""

        if existing:
            matched_count += 1
            cur_seo = existing.get("seo_meta") or {}
            cur_title = cur_seo.get("meta_title") or cur_seo.get("page_title") or "Default generated"
            cur_desc = cur_seo.get("meta_description") or "Default generated"
            status = "matched"
        else:
            not_found_count += 1
            if len(not_found_codes) < 20:
                not_found_codes.append(f"{raw_cc}·{code}")
            cur_title = "—"
            cur_desc = "—"
            status = "not_found"

        if len(sample_rows) < 30:
            sample_rows.append({
                "row_index": idx + 2,
                "country": raw_cc,
                "code": code,
                "title": existing.get("title") if existing else (str(row.get(mapping.get("title")) or "") if mapping.get("title") else "—"),
                "status": status,
                "current_meta_title": cur_title,
                "new_meta_title": new_meta_title or "(Keep current/generated)",
                "new_meta_description": new_meta_desc or "(Keep current/generated)",
                "keywords": new_keywords,
                "focus_keyword": new_focus_kw,
            })

    return {
        "ok": True,
        "total_rows": total_rows,
        "matched_count": matched_count,
        "not_found_count": not_found_count,
        "not_found_codes": not_found_codes,
        "sample_rows": sample_rows,
        "detected_mapping": {k: v for k, v in mapping.items() if v is not None},
    }


@router.post("/seo/commit")
async def commit_seo_excel_upload(
    file: UploadFile = File(...),
    country_code: str = Form("AU"),
    publish_live: bool = Form(True),
    current_user: dict = Depends(get_current_user),
):
    """Commit SEO attributes from Excel/CSV file to occupation_master in bulk.
    Optionally rebuilds and publishes the live SSR/SSG public atlas pages immediately.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin permissions required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    df = _parse_upload(content, file.filename)
    mapping = _detect_seo_columns(df.columns.tolist())

    if not mapping.get("code"):
        raise HTTPException(status_code=400, detail="Missing required 'Code' column")

    default_cc = (country_code or "AU").strip().upper()
    now = datetime.now(timezone.utc)
    updated_count = 0
    live_rebuilt_count = 0
    skipped_count = 0
    errors: List[str] = []

    # Optional SSG rebuild hook
    on_verified_hook = None
    if publish_live:
        try:
            from routers.seo_ssg import on_verified_hook as ssg_hook
            on_verified_hook = ssg_hook
        except Exception:
            pass

    for idx, row in df.iterrows():
        try:
            raw_code = str(row.get(mapping["code"]) or "").strip()
            if not raw_code or raw_code == "nan":
                skipped_count += 1
                continue

            raw_cc = str(row.get(mapping.get("country_code")) or "").strip().upper() if mapping.get("country_code") else ""
            if not raw_cc or raw_cc == "NAN":
                raw_cc = default_cc

            code = raw_code
            if "-" in raw_code:
                parts = raw_code.split("-", 1)
                if parts[0].upper() in ("AU", "CA", "NZ"):
                    raw_cc = parts[0].upper()
                    code = parts[1].strip()

            if code.endswith(".0"):
                code = code[:-2]

            existing = await OCCUPATION_MASTER.find_one(
                {"country_code": raw_cc, "code": code, "status": {"$ne": "superseded"}}
            )
            if not existing:
                skipped_count += 1
                continue

            # Merge SEO attributes with existing
            cur_seo = dict(existing.get("seo_meta") or {})

            def _get_val(key):
                if not mapping.get(key):
                    return None
                val = row.get(mapping[key])
                if val is None or pd.isna(val):
                    return None
                s = str(val).strip()
                return s if s and s != "nan" else None

            meta_title = _get_val("meta_title")
            meta_desc = _get_val("meta_description")
            keywords = _get_val("keywords")
            focus_kw = _get_val("focus_keyword")
            canonical = _get_val("canonical_url")
            og_title = _get_val("og_title")
            og_desc = _get_val("og_description")
            og_img = _get_val("og_image")
            tw_title = _get_val("twitter_title")
            tw_desc = _get_val("twitter_description")
            tw_img = _get_val("twitter_image")
            robots = _get_val("meta_robots")
            schema = _get_val("schema_type")

            if meta_title: cur_seo["meta_title"] = meta_title; cur_seo["page_title"] = meta_title
            if meta_desc: cur_seo["meta_description"] = meta_desc
            if keywords: cur_seo["keywords"] = keywords
            if focus_kw: cur_seo["focus_keyword"] = focus_kw
            if canonical: cur_seo["canonical_url"] = canonical
            if og_title: cur_seo["og_title"] = og_title
            if og_desc: cur_seo["og_description"] = og_desc
            if og_img: cur_seo["og_image"] = og_img
            if tw_title: cur_seo["twitter_title"] = tw_title
            if tw_desc: cur_seo["twitter_description"] = tw_desc
            if tw_img: cur_seo["twitter_image"] = tw_img
            if robots: cur_seo["meta_robots"] = robots
            if schema: cur_seo["schema_type"] = schema

            update_dict: Dict[str, Any] = {
                "seo_meta": cur_seo,
                "updated_at": now,
            }

            await OCCUPATION_MASTER.update_one(
                {"_id": existing["_id"]},
                {"$set": update_dict}
            )
            updated_count += 1

            # Trigger live public page rebuild if requested
            if publish_live and on_verified_hook:
                try:
                    await on_verified_hook(raw_cc, code)
                    live_rebuilt_count += 1
                except Exception as ssg_err:  # noqa: BLE001
                    errors.append(f"{raw_cc}·{code} live rebuild notice: {str(ssg_err)[:100]}")

        except Exception as row_err:  # noqa: BLE001
            errors.append(f"Row {idx + 2}: {str(row_err)[:120]}")

    # Write audit event
    await db["audit_logs"].insert_one({
        "id": str(uuid.uuid4()),
        "action": "occupation_master.bulk_seo_update",
        "user_id": current_user.get("id") or current_user.get("email"),
        "at": now,
        "summary": {
            "file_name": file.filename,
            "country_code": default_cc,
            "total_rows": len(df),
            "updated_count": updated_count,
            "live_rebuilt_count": live_rebuilt_count,
            "skipped_count": skipped_count,
            "publish_live": publish_live,
        },
    })

    return {
        "ok": True,
        "total_rows": len(df),
        "updated_count": updated_count,
        "live_rebuilt_count": live_rebuilt_count,
        "skipped_count": skipped_count,
        "errors": errors[:30],
    }

