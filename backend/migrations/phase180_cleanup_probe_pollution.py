"""Phase 18.0 — Cleanup probe-pollution on `occupation_master`.

Background
==========
Phase 17.1.3 testing accidentally PUT polluted content into the AU 111111
record (description=`Tester probe update …`, typical_tasks=`["probe task 1"…]`).
The real, official-grade content survived on the `ai_draft.*` sub-block, so
this migration restores it. Also catches any future test-probe pollution
(prefixes: ``Tester probe`` / ``probe task`` / ``test_`` / ``demo_``).

Behaviour
=========
For every `occupation_master` doc where:
  • `description` matches ``^(Tester probe|probe task|test_|demo_)``, OR
  • `typical_tasks` contains a value starting with ``probe task`` / ``test_``

  → if `ai_draft.description` is non-empty, restore it; else clear to "".
  → if `ai_draft.typical_tasks` is non-empty, restore it; else clear to [].

Idempotent: subsequent runs report 0 changes (the cleaned content no longer
matches the pollution regexes).

Wired into ``server.py`` startup AFTER the Phase 17.1.3 `occupation_id`
backfill so pollution gets cleaned on every boot.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, Dict

_POLLUTION_RE = re.compile(r"^(Tester probe|probe task|test_|demo_)", re.IGNORECASE)


def _is_polluted_text(s: Any) -> bool:
    return isinstance(s, str) and bool(_POLLUTION_RE.match(s.strip()))


def _is_polluted_tasks(tasks: Any) -> bool:
    if not isinstance(tasks, list):
        return False
    return any(_is_polluted_text(t) for t in tasks)


async def run_cleanup_probe_pollution(db) -> Dict[str, Any]:
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc).isoformat()
    cleaned_by_country: Dict[str, int] = {}
    cleaned_total = 0
    scanned = 0

    cur = coll.find(
        {},
        {
            "_id": 0,
            "occupation_id": 1,
            "country_code": 1,
            "code": 1,
            "description": 1,
            "typical_tasks": 1,
            "ai_draft": 1,
        },
    )
    async for d in cur:
        scanned += 1
        desc_polluted = _is_polluted_text(d.get("description"))
        tasks_polluted = _is_polluted_tasks(d.get("typical_tasks"))
        if not (desc_polluted or tasks_polluted):
            continue

        ai_draft = d.get("ai_draft") or {}
        set_payload: Dict[str, Any] = {"updated_at": now}

        if desc_polluted:
            restored = ai_draft.get("description") or ""
            set_payload["description"] = restored
        if tasks_polluted:
            restored_tasks = ai_draft.get("typical_tasks") or []
            set_payload["typical_tasks"] = restored_tasks

        # Match by canonical occupation_id when present, else fall back to (cc, code)
        if d.get("occupation_id"):
            q = {"occupation_id": d["occupation_id"]}
        else:
            q = {"country_code": d.get("country_code"), "code": d.get("code")}

        await coll.update_one(q, {"$set": set_payload})
        cc = (d.get("country_code") or "?").upper()
        cleaned_by_country[cc] = cleaned_by_country.get(cc, 0) + 1
        cleaned_total += 1

    return {
        "status": "ok",
        "scanned": scanned,
        "cleaned": cleaned_total,
        "by_country": cleaned_by_country,
    }
