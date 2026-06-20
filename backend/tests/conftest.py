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

# ── Env auto-load (idempotent) ────────────────────────────────────────────────
_ENV_PATH = pathlib.Path("/app/backend/.env")
if _ENV_PATH.exists():
    for _line in _ENV_PATH.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())


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
