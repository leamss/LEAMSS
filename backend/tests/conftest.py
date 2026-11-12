"""Option D / X2 — Test isolation conftest.

Provides robust event-loop, env-loading, and Mongo client fixtures so the
~290+ test suite passes regardless of test ordering. Resolves the recurring
Motor async teardown issue noted in handoff.

Auto-applied because of standard pytest conftest discovery.
"""
from __future__ import annotations

import asyncio
import os
import pathlib

import pytest

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# ── Env auto-load (idempotent) ────────────────────────────────────────────────
# Backend .env (MONGO_URL, DB_NAME, JWT_SECRET, etc.)
_this_dir = pathlib.Path(__file__).resolve().parent
for _envp in (
    pathlib.Path("/app/backend/.env"),
    pathlib.Path("/app/frontend/.env"),
    _this_dir.parent / ".env",
    _this_dir.parent.parent / "backend" / ".env",
):
    if _envp.exists():
        for _line in _envp.read_text().splitlines():
            if "=" in _line and not _line.startswith("#"):
                _k, _, _v = _line.partition("=")
                _k, _v = _k.strip(), _v.strip()
                if _k and _v and _k not in os.environ:
                    os.environ[_k] = _v

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "leamss_test")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_must_be_at_least_32_characters_long_for_security!")
os.environ.setdefault("DATA_IMPORT_STORAGE", str(_this_dir.parent / "storage" / "jsa_imports"))
os.environ.setdefault("STATE_NOM_STORAGE", str(_this_dir.parent / "storage" / "state_nominations"))
os.environ.setdefault("UPLOAD_DIR", str(_this_dir.parent / "uploads"))


# ── Session-scoped event loop (one per pytest run) ────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    """Override default function-scoped loop with a session-scoped one.

    This prevents `RuntimeError: Event loop is closed` cascades when Motor
    client connections (which bind to a loop) are reused across test modules.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Session-scoped sync Mongo client ──────────────────────────────────────────
@pytest.fixture(scope="session")
def sync_db():
    """Sync pymongo handle for direct DB seeding/cleanup in tests.

    Most tests use `requests` for HTTP + pymongo for setup, so a single
    session-scoped sync client is the most stable option.
    """
    from pymongo import MongoClient
    client = MongoClient(os.environ["MONGO_URL"])
    yield client[os.environ["DB_NAME"]]
    client.close()
