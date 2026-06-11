"""Phase 7.1 — KB Unification: Excel Import + Verification Hub.
Phase 17.0 — Persistent file storage + sanitised error messages + Auto-Fetch.

Endpoints under /api/kb-unified:
  POST   /import-anzsco-excel       — multipart upload → persistent storage → import
  POST   /import-anzsco-default     — re-run import using LATEST stored file
                                      (returns 409 NO_PRIOR_FILE with action choices
                                       when no stored file exists)
  POST   /auto-fetch-anzsco         — live-fetch AU codes from Home Affairs SOL
  GET    /import-files/latest       — metadata of the most-recent stored file
  GET    /import-files              — paginated history
  GET    /verification-hub          — unified count of draft/verified items
  GET    /anzsco/{four_digit_code}  — single 4-digit profile
  GET    /occupation-full/{code}    — 6-digit + 4-digit + template joined
"""
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from core.anzsco_excel_importer import (
    ANZSCO_4DIGIT, import_anzsco_excel, get_4digit_parent_code,
)
from core.auth import get_current_user
from core.database import db
from core import import_storage
from core.scrapers import home_affairs as home_affairs_scraper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kb-unified", tags=["kb-unified"])

OCCUPATIONS = db["occupation_master"]
COUNTRY_TEMPLATES = db["country_templates"]
COUNTRY_GUIDES = db["country_guides"]
POLICIES = db["protection_policies"]

ADMIN_ROLES = {"admin", "admin_owner"}

# Phase 17.0 — file metadata lives in MongoDB; bytes live under STORAGE_ROOT.
ANZSCO_SOURCE_TYPE = "anzsco_4digit"


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _user_display_name(user: dict) -> str:
    return user.get("name") or user.get("email") or user.get("id") or "admin"


def _no_prior_file_response(filename_hint: Optional[str] = None) -> JSONResponse:
    """Return a structured 409 the frontend can render as an action choice
    rather than a dead-end error. NEVER include any server path string."""
    msg = (
        "No previously imported Excel file was found. "
        "Please upload an ANZSCO Excel file to continue."
    )
    return JSONResponse(
        status_code=409,
        content={
            "code": "NO_PRIOR_FILE",
            "message": msg,
            "actions": [
                {"label": "Upload Excel", "kind": "upload"},
                {
                    "label": "Fetch Latest from Official Source",
                    "kind": "fetch_latest",
                    "endpoint": "/api/kb-unified/auto-fetch-anzsco",
                },
            ],
        },
    )


@router.post("/import-anzsco-excel")
async def upload_and_import(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Multipart upload an ANZSCO Excel — persist to durable storage, import to
    `anzsco_4digit_master`, then update the file row with the run summary.
    Response NEVER contains a server-internal path."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(400, "Only .xlsx files are supported")

    # Phase 17.0.1 — accept the standard xlsx mimetype OR generic streams
    # (curl uploads often arrive as application/octet-stream). Anything else
    # is almost certainly a junk upload from the browser file picker.
    ct = (file.content_type or "").lower()
    allowed_ct = {
        "",
        "application/octet-stream",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    }
    if ct and ct not in allowed_ct:
        raise HTTPException(
            400,
            "Uploaded file content-type is not an Excel workbook. Please pick a .xlsx file.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Empty file")

    # Phase 17.0.1 — pre-validate IN MEMORY before touching disk. Malformed
    # uploads (plain text, corrupt zip, missing sheets) must NOT get persisted.
    try:
        import_storage.validate_xlsx_bytes(contents, required_sheets=["Table_1"])
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    file_doc = await import_storage.save_import_file(
        db=db,
        source_type=ANZSCO_SOURCE_TYPE,
        data=contents,
        filename_original=file.filename,
        uploaded_by=current_user.get("id") or "admin",
        uploaded_by_name=_user_display_name(current_user),
    )

    # Run import against the persisted file.
    try:
        summary = await import_anzsco_excel(
            file_doc["storage_path"],
            imported_by=current_user.get("id") or "admin",
        )
        await import_storage.update_last_import_summary(
            db=db, file_id=file_doc["id"], summary=summary, status="imported",
        )
        # Reflect post-import state in the response (status flips ready→imported).
        file_doc["status"] = "imported"
        file_doc["last_import_summary"] = summary
        file_doc["last_imported_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        # Phase 17.0.1 — classify between user-error (4xx) and server-error (5xx).
        status_code, msg = import_storage.classify_upload_error(e)
        if status_code == 400:
            # Client-fault: roll back the on-disk artefact + DB row so junk
            # uploads don't accumulate. Caller gets the user-friendly message.
            await import_storage.delete_file(db, file_doc["id"])
            logger.warning(
                "Rejected malformed upload after persist (file_id=%s): %s",
                file_doc["id"], msg,
            )
            raise HTTPException(400, msg) from e
        # Genuine server fault — keep the row (marked failed) for forensics.
        await import_storage.update_last_import_summary(
            db=db,
            file_id=file_doc["id"],
            summary={"error": msg},
            status="failed",
        )
        logger.exception("Excel import failed for file_id=%s", file_doc["id"])
        raise HTTPException(500, msg) from e

    return {
        "ok": True,
        "file": import_storage.public_view(file_doc),
        "summary": summary,
    }


@router.post("/import-anzsco-default")
async def import_default(current_user: dict = Depends(get_current_user)):
    """Re-run import using the LATEST stored file for ANZSCO_SOURCE_TYPE.
    Returns 409 NO_PRIOR_FILE with structured `actions` if no file exists yet."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    latest = await import_storage.get_latest_file(db, ANZSCO_SOURCE_TYPE)
    if not latest:
        return _no_prior_file_response()
    if not os.path.exists(latest.get("storage_path", "")):
        # On-disk artefact missing (e.g. manual clean) — treat as no prior file.
        logger.warning(
            "[kb_unified] import_files row found but on-disk artefact missing for id=%s",
            latest.get("id"),
        )
        return _no_prior_file_response()

    try:
        summary = await import_anzsco_excel(
            latest["storage_path"],
            imported_by=current_user.get("id") or "admin",
        )
        await import_storage.update_last_import_summary(
            db=db, file_id=latest["id"], summary=summary, status="imported",
        )
    except Exception as e:
        await import_storage.update_last_import_summary(
            db=db, file_id=latest["id"], summary={"error": str(e)}, status="failed",
        )
        logger.exception("Re-import failed for file_id=%s", latest.get("id"))
        raise HTTPException(500, f"Re-import failed: {e}") from e

    return {
        "ok": True,
        "file": import_storage.public_view(latest),
        "summary": summary,
    }


@router.post("/auto-fetch-anzsco")
async def auto_fetch_anzsco(current_user: dict = Depends(get_current_user)):
    """Live-fetch the AU Skilled Occupation List from Home Affairs and upsert
    base `occupation_master` records. This is a 6-digit-code refresh — NOT a
    replacement for the ANZSCO 4-digit Excel import. Frontend should label the
    outcome accordingly using the `target_collection` field."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    actor = current_user.get("id") or "admin"
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        # Step 1 — live scrape (in-memory, no on-disk artefact)
        raw = home_affairs_scraper.fetch_raw_records()
        records = [home_affairs_scraper.normalize_record(r) for r in raw]

        # Step 2 — dedupe by code (prefer entries with a title)
        by_code: Dict[str, Dict[str, Any]] = {}
        for n in records:
            c = n.get("code")
            if not c:
                continue
            if c in by_code and not n.get("title"):
                continue
            by_code[c] = n

        # Step 3 — existing codes already in occupation_master (AU)
        existing_codes: set[str] = set()
        async for d in OCCUPATIONS.find(
            {"country_code": "AU"}, {"code": 1, "_id": 0}
        ):
            existing_codes.add(d.get("code") or "")

        created = 0
        updated = 0
        now_iso = fetched_at
        for code, n in by_code.items():
            base_doc = {
                "country_code": "AU",
                "code": code,
                "title": n.get("title") or "",
                "classification_version": n.get("classification_version") or "ANZSCO 2013",
                "classification_dual_code": n.get("classification_dual_code") or {},
                "anzsco_ref_url": n.get("anzsco_ref_url") or "",
                "visa_pathways": n.get("visa_pathways") or {},
                "pathway_list": n.get("pathway_list") or "",
                "assessing_authority": n.get("assessing_authority") or {},
                "last_scraped_at": now_iso,
                "last_scraped_by": "auto_fetch_anzsco",
                "updated_at": now_iso,
            }
            if code in existing_codes:
                await OCCUPATIONS.update_one(
                    {"country_code": "AU", "code": code}, {"$set": base_doc}
                )
                updated += 1
            else:
                base_doc.update({
                    "status": "verified",
                    "verification": {
                        "source": "home_affairs_skilled_occupation_list",
                        "auto_verified_at": now_iso,
                        "auto_verified_by": "auto_fetch_anzsco",
                        "method": "Home Affairs live scrape via /auto-fetch-anzsco",
                    },
                    "created_at": now_iso,
                    "anzsco_4digit_code": code[:4] if len(code) == 6 and code.isdigit() else None,
                    "anzsco_major_group_code": code[0] if code and code[0].isdigit() else None,
                })
                await OCCUPATIONS.insert_one(base_doc)
                created += 1
    except Exception as e:
        logger.exception("auto-fetch-anzsco failed")
        raise HTTPException(502, f"Auto-fetch failed: {e}") from e

    return {
        "ok": True,
        "source": "Home Affairs Skilled Occupation List",
        "source_url": home_affairs_scraper.SOURCE_URL,
        "target_collection": "occupation_master",
        "country_code": "AU",
        "fetched_at": fetched_at,
        "imported": created,
        "updated": updated,
        "skipped": 0,
        "total_processed": created + updated,
    }


@router.get("/import-files/latest")
async def get_latest_import_file(
    source_type: str = Query(ANZSCO_SOURCE_TYPE),
    current_user: dict = Depends(get_current_user),
):
    """Return metadata of the latest stored file for a source_type, or
    `{file: None}` when nothing has been uploaded yet. Never returns a path."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    latest = await import_storage.get_latest_file(db, source_type)
    return {"file": import_storage.public_view(latest)}


@router.get("/import-files")
async def list_import_files(
    source_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """Paginated history list — newest first. Used by Phase 17.1 import-history UI."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    rows = await import_storage.list_files(db, source_type, limit)
    return {"items": rows, "count": len(rows)}


@router.get("/verification-hub")
async def verification_hub(current_user: dict = Depends(get_current_user)):
    """Unified counts of pending verifications across all 4 KB entity types."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    async def count_by_status(coll, status_field="status"):
        out: Dict[str, int] = {}
        async for d in coll.aggregate([
            {"$group": {"_id": f"${status_field}", "count": {"$sum": 1}}},
        ]):
            out[d["_id"] or "none"] = d["count"]
        return out

    occ_counts = await count_by_status(OCCUPATIONS)
    template_counts = await count_by_status(COUNTRY_TEMPLATES)
    guide_counts = await count_by_status(COUNTRY_GUIDES)
    policy_counts = await count_by_status(POLICIES)
    anzsco_total = await ANZSCO_4DIGIT.count_documents({})

    # Pending lists (top 10 drafts per entity)
    pending_occupations = await OCCUPATIONS.find(
        {"status": {"$in": ["draft", None]}},
        {"_id": 0, "occupation_id": 1, "code": 1, "title": 1, "country_code": 1, "status": 1, "updated_at": 1},
    ).sort("updated_at", -1).to_list(10)
    pending_templates = await COUNTRY_TEMPLATES.find(
        {"status": {"$ne": "verified"}},
        {"_id": 0, "country_code": 1, "country_name": 1, "status": 1, "updated_at": 1},
    ).sort("updated_at", -1).to_list(10)
    pending_guides = await COUNTRY_GUIDES.find(
        {"status": {"$ne": "verified"}},
        {"_id": 0, "country_code": 1, "name": 1, "status": 1, "updated_at": 1},
    ).sort("updated_at", -1).to_list(10)
    pending_policies = await POLICIES.find(
        {"status": {"$ne": "verified"}},
        {"_id": 0, "policy_id": 1, "title": 1, "status": 1, "updated_at": 1},
    ).sort("updated_at", -1).to_list(10)

    return {
        "summary": {
            "occupation_master": {
                "counts": occ_counts,
                "verified_pct": _pct(occ_counts.get("verified", 0), sum(occ_counts.values()) or 1),
            },
            "country_templates": {
                "counts": template_counts,
                "verified_pct": _pct(template_counts.get("verified", 0), sum(template_counts.values()) or 1),
            },
            "country_guides": {
                "counts": guide_counts,
                "verified_pct": _pct(guide_counts.get("verified", 0), sum(guide_counts.values()) or 1),
            },
            "protection_policies": {
                "counts": policy_counts,
                "verified_pct": _pct(policy_counts.get("verified", 0), sum(policy_counts.values()) or 1),
            },
            "anzsco_4digit_master": {
                "total_codes": anzsco_total,
                "data_source": "ABS Feb 2026",
            },
        },
        "pending_lists": {
            "occupations": pending_occupations,
            "country_templates": pending_templates,
            "country_guides": pending_guides,
            "protection_policies": pending_policies,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _pct(num: int, denom: int) -> float:
    if not denom:
        return 0.0
    return round((num / denom) * 100, 1)


@router.get("/anzsco/{four_digit_code}")
async def get_anzsco_profile(four_digit_code: str):
    """Public-readable 4-digit ANZSCO profile. Used by report renderer + occupation viewer."""
    doc = await ANZSCO_4DIGIT.find_one({"code": four_digit_code}, {"_id": 0})
    if not doc:
        raise HTTPException(404, f"ANZSCO 4-digit code {four_digit_code} not found")
    return doc


@router.get("/occupation-full/{code}")
async def get_occupation_full(code: str, current_user: dict = Depends(get_current_user)):
    """Returns a 6-digit occupation_master document joined with:
      - its 4-digit ANZSCO parent profile
      - linked country_template
      - linked country_guide
    One call → everything report renderer needs.
    """
    if not _is_admin(current_user) and not current_user:
        raise HTTPException(401, "Auth required")

    occ = await OCCUPATIONS.find_one({"code": code}, {"_id": 0})
    if not occ:
        raise HTTPException(404, f"Occupation code {code} not found")

    parent_code = await get_4digit_parent_code(code)
    anzsco_profile = None
    if parent_code:
        anzsco_profile = await ANZSCO_4DIGIT.find_one({"code": parent_code}, {"_id": 0})

    country_code = occ.get("country_code")
    template = None
    guide = None
    if country_code:
        template = await COUNTRY_TEMPLATES.find_one({"country_code": country_code}, {"_id": 0})
        guide = await COUNTRY_GUIDES.find_one({"country_code": country_code}, {"_id": 0})

    return {
        "occupation": occ,
        "anzsco_4digit_parent": anzsco_profile,
        "country_template": template,
        "country_guide": guide,
    }
