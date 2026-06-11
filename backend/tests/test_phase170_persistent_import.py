"""Phase 17.0 — Verification Hub persistent-file import + sanitised errors.

Tests cover:
  1. Upload creates a real `import_files` row + on-disk artefact, response is sanitised
  2. Second upload demotes the first (only one is_latest per source_type)
  3. Same-bytes upload de-dupes (reuses file_id)
  4. `/import-anzsco-default` with no prior file returns HTTP 409 + structured action choices
  5. `/import-anzsco-default` with a prior file works
  6. Aggregate: no endpoint EVER leaks `/tmp` or `/app/backend/storage` to client
  7. `/auto-fetch-anzsco` runs against live Home Affairs (network-dependent)
  8. Phase 7.1 seeder is idempotent — 5 templates + 1 default policy after two runs

Run:
    cd /app/backend && python -m pytest tests/test_phase170_persistent_import.py -v
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import httpx
import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

API_BASE = os.environ.get("AUDIT_API_BASE", "http://localhost:8001/api")
ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"
SRC = "anzsco_4digit"

_db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


# ─── Helpers ────────────────────────────────────────────────────────────────
def _login_token() -> str:
    r = httpx.post(
        f"{API_BASE}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers():
    return {"Authorization": f"Bearer {_login_token()}"}


def _build_min_xlsx(title_suffix: str = "") -> bytes:
    """Tiny valid ANZSCO Excel — 1 row in Table_1 with all 8 expected columns,
    Table_2 with code + description, empty other tables. `title_suffix` lets each
    test produce a distinct sha256 when needed."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Table_1"
    # Table_1 expects 8 columns: code, title, employed, pt%, female%, median$, age, growth
    headers1 = ["Code", "Title", "Employed", "PT%", "Female%", "MedianAUD", "MedianAge", "Growth"]
    for i, h in enumerate(headers1, start=1):
        ws.cell(row=7, column=i).value = h
    row1 = ["2613", f"Software & Applications Programmers{title_suffix}", 100000, 12.5, 22.3, 1850, 38, 5]
    for i, v in enumerate(row1, start=1):
        ws.cell(row=8, column=i).value = v

    # Table_2 (descriptions) needs at least 3 cols
    ws2 = wb.create_sheet("Table_2")
    ws2.cell(row=7, column=1).value = "Code"
    ws2.cell(row=7, column=2).value = "Title"
    ws2.cell(row=7, column=3).value = "Description"
    ws2.cell(row=8, column=1).value = "2613"
    ws2.cell(row=8, column=2).value = "Software & Applications Programmers"
    ws2.cell(row=8, column=3).value = "Designs, develops, tests, deploys and maintains software systems."

    # Empty placeholder sheets so the importer doesn't error on missing tabs
    for name in ["Table_3", "Table_4", "Table_5", "Table_6", "Table_7", "Table_8", "Table_9"]:
        s = wb.create_sheet(name)
        for i in range(1, 9):
            s.cell(row=7, column=i).value = f"col{i}"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _drop_import_files():
    await _db["import_files"].delete_many({})


async def _wipe_storage_dir():
    # Best-effort cleanup; matches what `import_storage.STORAGE_ROOT` controls.
    from core import import_storage
    root: Path = import_storage.STORAGE_ROOT / SRC
    if root.exists():
        for f in root.iterdir():
            try:
                f.unlink()
            except OSError:
                pass


PATH_LEAK_PATTERNS = ("/tmp/", "/app/backend/storage", "storage_path")


def _assert_no_path_leak(payload: Any, label: str = "") -> None:
    s = json.dumps(payload, default=str)
    for p in PATH_LEAK_PATTERNS:
        assert p not in s, (
            f"Path leak '{p}' found in {label} response: {s[:200]}"
        )


# ─── Tests ──────────────────────────────────────────────────────────────────
def test_1_upload_creates_import_files_row(auth_headers):
    """Upload creates DB row + on-disk file. Response is sanitised."""
    _async(_drop_import_files())
    _async(_wipe_storage_dir())

    data = _build_min_xlsx("_t1")
    r = httpx.post(
        f"{API_BASE}/kb-unified/import-anzsco-excel",
        headers=auth_headers,
        files={"file": ("anzsco_t1.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        timeout=30,
    )
    assert r.status_code == 200, f"upload failed: {r.status_code} · {r.text[:200]}"
    body = r.json()
    assert body.get("ok") is True
    assert "file" in body
    assert body["file"]["filename_original"] == "anzsco_t1.xlsx"
    assert body["file"]["is_latest"] is True
    assert body["file"]["status"] == "imported"
    assert body["file"]["sha256"]
    # No server path in any response field
    _assert_no_path_leak(body, "upload")
    assert "storage_path" not in body["file"], "storage_path leaked into client payload"

    # DB row exists with is_latest=True
    row = _async(_db["import_files"].find_one({"id": body["file"]["id"]}))
    assert row is not None
    assert row["is_latest"] is True
    # On-disk artefact exists
    assert os.path.exists(row["storage_path"]), "on-disk artefact missing"
    assert row["storage_path"].endswith(".xlsx")


def test_2_second_upload_demotes_first(auth_headers):
    """Two distinct uploads — only one is_latest=True; newer wins."""
    _async(_drop_import_files())
    _async(_wipe_storage_dir())
    httpx.post(
        f"{API_BASE}/kb-unified/import-anzsco-excel",
        headers=auth_headers,
        files={"file": ("first.xlsx", _build_min_xlsx("_v1"), "application/octet-stream")},
        timeout=30,
    )
    httpx.post(
        f"{API_BASE}/kb-unified/import-anzsco-excel",
        headers=auth_headers,
        files={"file": ("second.xlsx", _build_min_xlsx("_v2"), "application/octet-stream")},
        timeout=30,
    )
    latest_rows = _async(_db["import_files"].find({"source_type": SRC, "is_latest": True}).to_list(10))
    assert len(latest_rows) == 1, f"Expected exactly 1 is_latest, got {len(latest_rows)}"
    assert latest_rows[0]["filename_original"] == "second.xlsx"


def test_3_same_hash_dedupe(auth_headers):
    """Uploading identical bytes twice MUST NOT create a duplicate DB row."""
    _async(_drop_import_files())
    _async(_wipe_storage_dir())
    payload = _build_min_xlsx("_dedupe")
    r1 = httpx.post(
        f"{API_BASE}/kb-unified/import-anzsco-excel",
        headers=auth_headers,
        files={"file": ("same.xlsx", payload, "application/octet-stream")},
        timeout=30,
    )
    r2 = httpx.post(
        f"{API_BASE}/kb-unified/import-anzsco-excel",
        headers=auth_headers,
        files={"file": ("same.xlsx", payload, "application/octet-stream")},
        timeout=30,
    )
    assert r1.status_code == 200 and r2.status_code == 200
    # Same file_id reused on second call
    assert r1.json()["file"]["id"] == r2.json()["file"]["id"]
    rows = _async(_db["import_files"].find({"source_type": SRC}).to_list(10))
    assert len(rows) == 1, f"Dedupe failed — got {len(rows)} rows, expected 1"


def test_4_reimport_with_no_prior_returns_409(auth_headers):
    """When import_files is empty, /import-anzsco-default must return a
    structured 409 with action choices (NEVER a /tmp path)."""
    _async(_drop_import_files())
    _async(_wipe_storage_dir())
    r = httpx.post(
        f"{API_BASE}/kb-unified/import-anzsco-default",
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 409, f"Expected 409, got {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert body.get("code") == "NO_PRIOR_FILE"
    assert "message" in body and body["message"]
    assert "/tmp" not in body["message"], f"Path leaked in 409 message: {body['message']}"
    assert isinstance(body.get("actions"), list)
    assert len(body["actions"]) >= 2
    kinds = {a.get("kind") for a in body["actions"]}
    assert {"upload", "fetch_latest"}.issubset(kinds)
    _assert_no_path_leak(body, "409 NO_PRIOR_FILE")


def test_5_reimport_with_prior_works(auth_headers):
    """After upload, /import-anzsco-default re-imports the stored file."""
    _async(_drop_import_files())
    _async(_wipe_storage_dir())
    httpx.post(
        f"{API_BASE}/kb-unified/import-anzsco-excel",
        headers=auth_headers,
        files={"file": ("prior.xlsx", _build_min_xlsx("_t5"), "application/octet-stream")},
        timeout=30,
    )
    r = httpx.post(
        f"{API_BASE}/kb-unified/import-anzsco-default",
        headers=auth_headers,
        timeout=30,
    )
    assert r.status_code == 200, f"Re-import failed: {r.status_code} · {r.text[:200]}"
    body = r.json()
    assert body.get("ok") is True
    assert body.get("summary")
    assert body["file"]["filename_original"] == "prior.xlsx"
    _assert_no_path_leak(body, "re-import success")


def test_6_response_never_leaks_server_path(auth_headers):
    """Sweep through all 3 KB-unified endpoints with various inputs and assert
    no response body ever contains /tmp or /app/backend/storage."""
    _async(_drop_import_files())
    _async(_wipe_storage_dir())

    # GET latest empty
    r = httpx.get(
        f"{API_BASE}/kb-unified/import-files/latest?source_type={SRC}",
        headers=auth_headers, timeout=10,
    )
    _assert_no_path_leak(r.json(), "latest-empty")
    assert r.json()["file"] is None

    # 409 no prior
    r = httpx.post(f"{API_BASE}/kb-unified/import-anzsco-default", headers=auth_headers, timeout=10)
    _assert_no_path_leak(r.json(), "no-prior 409")

    # Upload + verify
    r = httpx.post(
        f"{API_BASE}/kb-unified/import-anzsco-excel",
        headers=auth_headers,
        files={"file": ("scan.xlsx", _build_min_xlsx("_t6"), "application/octet-stream")},
        timeout=30,
    )
    _assert_no_path_leak(r.json(), "upload-success")

    # GET latest populated
    r = httpx.get(
        f"{API_BASE}/kb-unified/import-files/latest?source_type={SRC}",
        headers=auth_headers, timeout=10,
    )
    _assert_no_path_leak(r.json(), "latest-populated")

    # GET history list
    r = httpx.get(
        f"{API_BASE}/kb-unified/import-files?source_type={SRC}&limit=10",
        headers=auth_headers, timeout=10,
    )
    _assert_no_path_leak(r.json(), "history-list")

    # POST re-import
    r = httpx.post(f"{API_BASE}/kb-unified/import-anzsco-default", headers=auth_headers, timeout=30)
    _assert_no_path_leak(r.json(), "reimport-success")


def test_7_auto_fetch_anzsco_runs(auth_headers):
    """Live scrape Home Affairs SOL. Network-dependent — skips if backend says 502."""
    r = httpx.post(
        f"{API_BASE}/kb-unified/auto-fetch-anzsco", headers=auth_headers, timeout=60,
    )
    if r.status_code == 502:
        pytest.skip("Network-dependent test — Home Affairs unreachable")
    assert r.status_code == 200, f"auto-fetch failed: {r.status_code} · {r.text[:200]}"
    body = r.json()
    assert body.get("ok") is True
    assert body.get("source") == "Home Affairs Skilled Occupation List"
    assert body.get("target_collection") == "occupation_master"
    assert isinstance(body.get("imported"), int)
    assert isinstance(body.get("updated"), int)
    # At least the 708 existing AU codes should be matched (updated) or new
    assert body["imported"] + body["updated"] >= 100
    _assert_no_path_leak(body, "auto-fetch")


def test_8_phase71_seeder_idempotent():
    """Phase 7.1 seeder must not duplicate templates/policy on re-run."""
    from migrations.phase71_kb_unification import run_idempotent
    _async(run_idempotent(_db))  # first call (or no-op if startup already ran)
    _async(run_idempotent(_db))  # second call — should be all "existed"

    templates = _async(_db["country_templates"].find({}).to_list(50))
    cc_set = {t.get("country_code") for t in templates}
    assert {"AU", "CA", "NZ", "UK", "USA"}.issubset(cc_set), (
        f"Missing seed template(s): expected AU/CA/NZ/UK/USA, got {cc_set}"
    )
    # No duplicates per country
    from collections import Counter
    counts = Counter(t.get("country_code") for t in templates)
    dupes = [cc for cc, n in counts.items() if n > 1]
    assert not dupes, f"Duplicate templates for {dupes}"

    # Exactly 1 default protection policy
    default_policies = _async(
        _db["protection_policies"].find({"is_default_leamss": True}).to_list(10)
    )
    assert len(default_policies) == 1, (
        f"Expected exactly 1 default protection policy, got {len(default_policies)}"
    )
