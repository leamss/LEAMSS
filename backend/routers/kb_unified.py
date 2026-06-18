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

    # Phase 17.0.2 — schema-shape pre-check (sheets + Code/Title cols + data row).
    # Raises InvalidExcelSchemaError which we map to a 400. NOTHING is persisted
    # on failure here — the DB row + on-disk artefact are only created after
    # both content + schema validation pass.
    try:
        from core.anzsco_excel_importer import (
            REQUIRED_SHEETS,
            REQUIRED_HEADER_ALIASES,
            HEADER_ROW,
        )
        import_storage.validate_xlsx_schema(
            contents,
            required_sheets=list(REQUIRED_SHEETS),
            header_row=HEADER_ROW,
            primary_sheet="Table_1",
            required_header_aliases=REQUIRED_HEADER_ALIASES,
        )
    except import_storage.InvalidExcelSchemaError as e:
        raise HTTPException(400, str(e)) from e

    file_doc = await import_storage.save_import_file(
        db=db,
        source_type=ANZSCO_SOURCE_TYPE,
        data=contents,
        filename_original=file.filename,
        uploaded_by=current_user.get("id") or "admin",
        uploaded_by_name=_user_display_name(current_user),
    )

    # Phase 19.6 — register a batch for audit visibility (bulk upsert path:
    # granular revoke is not supported here — marked audit_only).
    from services import import_batch_service as ibs
    batch = await ibs.open_batch(
        db,
        ingestion_path="phase_17_kb_unified",
        endpoint="POST /api/kb-unified/import-anzsco-excel",
        uploaded_by=current_user.get("id") or "admin",
        uploaded_by_name=_user_display_name(current_user),
        file_name=file.filename or "anzsco.xlsx",
        file_hash=ibs.file_sha256(contents),
        file_size_bytes=len(contents),
        target_collection="anzsco_4digit_master",
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
        # Phase 19.6 — close batch as audit-only (no granular revoke)
        await ibs.close_batch(
            db, batch,
            total_rows=int(summary.get("imported", 0) or 0) + int(summary.get("skipped", 0) or 0)
                        + int(summary.get("updated", 0) or 0),
            status="committed",
        )
        await db["import_batches"].update_one(
            {"batch_id": batch["batch_id"]},
            {"$set": {
                "is_revocable": False,
                "audit_only": True,
                "non_revocable_reason": "bulk_upsert_audit_only",
                "counts.imported": int(summary.get("imported", 0) or 0),
                "counts.updated": int(summary.get("updated", 0) or 0),
                "counts.skipped": int(summary.get("skipped", 0) or 0),
            }},
        )
        # Reflect post-import state in the response (status flips ready→imported).
        file_doc["status"] = "imported"
        file_doc["last_import_summary"] = summary
        file_doc["last_imported_at"] = datetime.now(timezone.utc).isoformat()
        file_doc["batch_id"] = batch["batch_id"]
    except Exception as e:
        # Phase 19.6 — mark batch as failed before classifying error
        try:
            await db["import_batches"].update_one(
                {"batch_id": batch["batch_id"]},
                {"$set": {"status": "failed", "is_revocable": False,
                          "audit_only": True, "non_revocable_reason": "import_failed"}},
            )
        except Exception:  # noqa: BLE001
            pass
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
    """Backwards-compat alias — forwards to /auto-fetch-country?country=AU.
    Original Phase 17.0 entry point; new code should target /auto-fetch-country."""
    return await auto_fetch_country({"country": "AU"}, current_user=current_user)


# Map of country → (label, source list, async fn(db, actor) → summary dict)
async def _run_au_fetch(db, actor: str) -> Dict[str, Any]:
    """AU: live Home Affairs SOL → occupation_master (existing 17.0 logic)."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    raw = home_affairs_scraper.fetch_raw_records()
    records = [home_affairs_scraper.normalize_record(r) for r in raw]
    by_code: Dict[str, Dict[str, Any]] = {}
    for n in records:
        c = n.get("code")
        if not c:
            continue
        if c in by_code and not n.get("title"):
            continue
        by_code[c] = n
    existing: set[str] = set()
    async for d in OCCUPATIONS.find({"country_code": "AU"}, {"code": 1, "_id": 0}):
        existing.add(d.get("code") or "")
    created = updated = 0
    for code, n in by_code.items():
        base = {
            "country_code": "AU", "code": code, "title": n.get("title") or "",
            "classification_version": n.get("classification_version") or "ANZSCO 2013",
            "anzsco_ref_url": n.get("anzsco_ref_url") or "",
            "visa_pathways": n.get("visa_pathways") or {},
            "pathway_list": n.get("pathway_list") or "",
            "assessing_authority": n.get("assessing_authority") or {},
            "last_scraped_at": fetched_at, "last_scraped_by": "auto_fetch_country",
            "updated_at": fetched_at,
        }
        if code in existing:
            await OCCUPATIONS.update_one({"country_code": "AU", "code": code}, {"$set": base})
            updated += 1
        else:
            base.update({
                "status": "verified",
                "verification": {
                    "source": "home_affairs_skilled_occupation_list",
                    "auto_verified_at": fetched_at,
                    "auto_verified_by": "auto_fetch_country",
                    "method": "Home Affairs live scrape via /auto-fetch-country",
                },
                "created_at": fetched_at,
                "anzsco_4digit_code": code[:4] if len(code) == 6 and code.isdigit() else None,
            })
            await OCCUPATIONS.insert_one(base)
            created += 1
    return {
        "country": "AU",
        "source": "Home Affairs Skilled Occupation List",
        "source_urls": [home_affairs_scraper.SOURCE_URL],
        "imported": created, "updated": updated, "skipped": 0,
        "fetched_at": fetched_at, "status": "success", "errors": [],
    }


async def _run_ca_fetch(db, actor: str) -> Dict[str, Any]:
    """CA: StatCan NOC 2021 + IRCC EE rounds + IRCC EE streams.

    Phase 17.1.1 — Two-phase: (1) run each enrichment scraper to apply diffs;
    (2) touch-pass: stamp `verification.auto_verified_at` + `verification.source`
    + `last_scraped_at` on EVERY CA record so the audit trail reflects this fetch.
    Scrapers return counts nested under `r["counts"]` — not flat — we read both."""
    started = datetime.now(timezone.utc)
    fetched_at = started.isoformat()
    errors: List[str] = []
    sources: List[str] = []
    source_urls: List[str] = []
    total_created = total_skipped = 0

    scraper_calls = [
        ("StatCan NOC 2021", "noc_canada"),
        ("IRCC Express Entry Rounds", "ircc_round_cutoffs"),
        ("IRCC EE Category-Based Streams", "ircc_ee_streams"),
    ]
    for label, mod_name in scraper_calls:
        try:
            mod = __import__(f"core.scrapers.{mod_name}", fromlist=[mod_name])
            r = await mod.apply_to_db(db, dry_run=False, actor=actor)
            counts = r.get("counts") or {}  # ← the fix: counts is NESTED
            total_created += int(counts.get("created", 0) or r.get("created", 0))
            total_skipped += int(counts.get("skipped_unchanged", 0) or r.get("skipped_unchanged", 0))
            sources.append(label)
            url = r.get("source_url") or getattr(mod, "SOURCE_URL", "")
            if url:
                source_urls.append(url)
        except Exception as e:  # noqa: BLE001 — propagate to response, never silently 0+0
            logger.exception("CA scraper %s failed", mod_name)
            errors.append(f"{mod_name}: {type(e).__name__}: {e}"[:500])

    # Phase 17.1.1 touch-pass — refresh verification stamp on every CA record so
    # admin sees a real "updated" count and Last-Verified column populates.
    touch_result = await OCCUPATIONS.update_many(
        {"country_code": "CA"},
        {"$set": {
            "verification.auto_verified_at": fetched_at,
            "verification.source": sources[0] if sources else "StatCan NOC 2021",
            "verification.auto_verified_by": "auto_fetch_country",
            "verification.method": "Phase 17.1.1 auto-fetch — StatCan NOC + IRCC enrichment",
            "last_scraped_at": fetched_at,
            "last_scraped_by": "auto_fetch_country",
            "updated_at": fetched_at,
        }},
    )

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    status = "failed" if errors and not sources else ("partial" if errors else "success")
    return {
        "country": "CA",
        "source": " + ".join(sources) if sources else "StatCan NOC 2021 (no scraper ran)",
        "source_urls": source_urls,
        "imported": total_created,
        "updated": int(getattr(touch_result, "modified_count", 0)),
        "skipped": total_skipped,
        "fetched_at": fetched_at,
        "duration_seconds": round(duration, 2),
        "status": status,
        "errors": errors[:5],
    }


async def _run_nz_fetch(db, actor: str) -> Dict[str, Any]:
    """NZ: ANZSCO seed + Green List + AEWV/SMC. Same two-phase pattern as CA."""
    started = datetime.now(timezone.utc)
    fetched_at = started.isoformat()
    errors: List[str] = []
    sources: List[str] = []
    source_urls: List[str] = []
    total_created = total_skipped = 0

    scraper_calls = [
        ("INZ National Occupation List", "nz_anzsco_seed"),
        ("INZ Green List", "nz_green_list"),
        ("INZ AEWV / SMC", "nz_aewv_smc"),
    ]
    for label, mod_name in scraper_calls:
        try:
            mod = __import__(f"core.scrapers.{mod_name}", fromlist=[mod_name])
            r = await mod.apply_to_db(db, dry_run=False, actor=actor)
            counts = r.get("counts") or {}
            total_created += int(counts.get("created", 0) or r.get("created", 0))
            total_skipped += int(counts.get("skipped_unchanged", 0) or r.get("skipped_unchanged", 0))
            sources.append(label)
            url = r.get("source_url") or getattr(mod, "SOURCE_URL", "")
            if url:
                source_urls.append(url)
        except Exception as e:  # noqa: BLE001
            logger.exception("NZ scraper %s failed", mod_name)
            errors.append(f"{mod_name}: {type(e).__name__}: {e}"[:500])

    touch_result = await OCCUPATIONS.update_many(
        {"country_code": "NZ"},
        {"$set": {
            "verification.auto_verified_at": fetched_at,
            "verification.source": sources[0] if sources else "INZ National Occupation List",
            "verification.auto_verified_by": "auto_fetch_country",
            "verification.method": "Phase 17.1.1 auto-fetch — INZ Green List + AEWV enrichment",
            "last_scraped_at": fetched_at,
            "last_scraped_by": "auto_fetch_country",
            "updated_at": fetched_at,
        }},
    )

    duration = (datetime.now(timezone.utc) - started).total_seconds()
    status = "failed" if errors and not sources else ("partial" if errors else "success")
    return {
        "country": "NZ",
        "source": " + ".join(sources) if sources else "INZ Green List (no scraper ran)",
        "source_urls": source_urls,
        "imported": total_created,
        "updated": int(getattr(touch_result, "modified_count", 0)),
        "skipped": total_skipped,
        "fetched_at": fetched_at,
        "duration_seconds": round(duration, 2),
        "status": status,
        "errors": errors[:5],
    }


@router.post("/auto-fetch-country")
async def auto_fetch_country(
    body: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
):
    """Live-fetch occupation data for AU, CA, NZ, or ALL three sequentially.
    Each run writes an audit row to `import_runs`. Response per-country
    breakdown includes source label, URLs, counts, and duration."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    country = (body or {}).get("country", "AU")
    country = str(country).upper()
    if country not in ("AU", "CA", "NZ", "ALL"):
        raise HTTPException(400, "country must be one of AU, CA, NZ, ALL")
    actor = current_user.get("id") or "admin"
    actor_name = _user_display_name(current_user)

    countries = ["AU", "CA", "NZ"] if country == "ALL" else [country]
    fetchers = {"AU": _run_au_fetch, "CA": _run_ca_fetch, "NZ": _run_nz_fetch}
    results: List[Dict[str, Any]] = []
    runs_coll = db["import_runs"]

    for c in countries:
        started_at = datetime.now(timezone.utc)
        run_doc: Dict[str, Any] = {
            "id": __import__("uuid").uuid4().hex,
            "method": "auto_fetch",
            "country": c,
            "triggered_by": actor,
            "triggered_by_name": actor_name,
            "started_at": started_at.isoformat(),
            "completed_at": None,
            "duration_seconds": None,
            "status": "running",
            "source": "", "source_urls": [],
            "summary": {"imported": 0, "updated": 0, "skipped": 0, "errors": []},
            "created_at": started_at.isoformat(),
        }
        await runs_coll.insert_one(run_doc)
        try:
            r = await fetchers[c](db, actor)
        except Exception as e:
            logger.exception("auto-fetch %s failed", c)
            completed = datetime.now(timezone.utc)
            r = {
                "country": c, "source": "(failed)",
                "source_urls": [], "imported": 0, "updated": 0, "skipped": 0,
                "fetched_at": completed.isoformat(),
                "status": "failed", "errors": [f"{type(e).__name__}: {e}"],
            }
        completed = datetime.now(timezone.utc)
        dur = (completed - started_at).total_seconds()
        r["duration_seconds"] = round(dur, 2)
        await runs_coll.update_one(
            {"id": run_doc["id"]},
            {"$set": {
                "completed_at": completed.isoformat(),
                "duration_seconds": round(dur, 2),
                "status": r.get("status", "success"),
                "source": r.get("source", ""),
                "source_urls": r.get("source_urls", []),
                "summary": {
                    "imported": r.get("imported", 0),
                    "updated": r.get("updated", 0),
                    "skipped": r.get("skipped", 0),
                    "errors": r.get("errors", [])[:50],
                },
            }},
        )
        results.append(r)

    totals = {
        "imported": sum(r.get("imported", 0) for r in results),
        "updated": sum(r.get("updated", 0) for r in results),
        "skipped": sum(r.get("skipped", 0) for r in results),
        "duration_seconds": round(sum(r.get("duration_seconds", 0) for r in results), 2),
    }
    overall_ok = all(r.get("status") in ("success", "partial") for r in results)
    return {"ok": overall_ok, "results": results, "totals": totals}


@router.get("/import-runs")
async def list_import_runs(
    country: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """Audit history for /auto-fetch-country runs."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    q: Dict[str, Any] = {}
    if country:
        q["country"] = country.upper()
    rows: List[Dict[str, Any]] = []
    async for d in db["import_runs"].find(q, {"_id": 0}).sort("started_at", -1).limit(limit):
        rows.append(d)
    return {"items": rows, "count": len(rows)}


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
