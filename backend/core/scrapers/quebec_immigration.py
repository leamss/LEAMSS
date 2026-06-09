"""Phase 10.7 · Quebec PSTQ + PEQ Legacy seed (Canada's special-stream immigration).

Quebec is the ONLY Canadian province that runs its own immigration system —
distinct from the federal IRCC Express Entry and from the 11 PNPs. This module
adds Quebec coverage under the same 🇨🇦 CA atlas country (just like AU's NSW
state-by-state).

Active programs (2026):
  • PSTQ — Programme de sélection des travailleurs qualifiés
    (Current main skilled-worker stream — replaced PEQ in 2025)
    4 streams (Sections A/B/C/D)
  • PEQ — Programme de l'expérience québécoise
    (Streams ended for new permanent applicants in 2025 — kept for legacy/audit)
  • Worker Selection Programs (regular/business/investor) — out of scope here

Quebec uses **FEER** (Federal Equivalence Education Requirement) which is
identical to NOC 2021's TEER classification (2nd digit of 5-digit code).

Official source: https://www.quebec.ca/en/immigration/permanent/skilled-workers

This module is DETERMINISTIC — no scraping, no network calls.
Quebec publishes priority occupation lists per draw, not as a single static list —
admin extends via the existing CSV / AI-Extract tools as draws come out.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Set

SOURCE_NAME = "quebec_immigration_2026"
SOURCE_URL = "https://www.quebec.ca/en/immigration/permanent/skilled-workers"

# ─── PSTQ — 4 Sections (current active program) ────────────────────────────
PSTQ_PROGRAM: Dict[str, Any] = {
    "id": "pstq",
    "name": "Programme de sélection des travailleurs qualifiés (PSTQ)",
    "official_url": "https://www.quebec.ca/en/immigration/permanent/skilled-workers/skilled-worker-selection-program",
    "started": "2024-11",
    "status": "active",
    "sections": [
        {
            "id": "pstq_a",
            "name": "Section A — Skilled Workers (priority TEER 0-2)",
            "feer_eligible": [0, 1, 2],
            "french_required": {"oral": 7, "written": 5},
            "notes": "Priority high-skill stream. Higher French requirement.",
        },
        {
            "id": "pstq_b",
            "name": "Section B — Skilled Workers (priority TEER 3-5)",
            "feer_eligible": [3, 4, 5],
            "french_required": {"oral": 5, "written": None},
            "notes": "Lower French bar. Aimed at trades + service occupations.",
        },
        {
            "id": "pstq_c",
            "name": "Section C — Regulated Professions",
            "feer_eligible": [0, 1, 2, 3, 4, 5],
            "french_required": {"oral": 7, "written": 5},
            "notes": "Requires authorization to practice in Quebec (regulated body licence).",
        },
        {
            "id": "pstq_d",
            "name": "Section D — Quebec-graduated Applicants",
            "feer_eligible": [0, 1, 2, 3, 4, 5],
            "french_required": {"oral": 7, "written": 5},
            "notes": "For candidates who completed eligible Quebec post-secondary studies.",
        },
    ],
    # Quebec's published priority sectors (in-demand 2026)
    "priority_sectors": [
        "information_technology",
        "engineering",
        "healthcare",
        "construction",
        "skilled_trades",
        "manufacturing",
        "logistics_transport",
        "education_childcare",
    ],
    # Tier-A (TEER 0-2) priority NOCs commonly invited in PSTQ Section A draws
    # These are seeds — admin extends via draw-specific CSV uploads
    "priority_nocs_section_a": [
        # IT (high invitations)
        "21231", "21232", "21233", "21234", "21311", "21221", "21222",
        # Engineering
        "21300", "21301", "21310", "21321", "21331",
        # Healthcare professionals
        "31301", "31302", "31300", "31100", "31101", "31102",
        # Senior managers / regulated
        "20012", "20011", "10010",
    ],
    "priority_nocs_section_b": [
        # Trades (TEER 2-3)
        "72100", "72106", "72200", "72201", "72300", "72310", "72400", "72500",
        # Healthcare assistants (TEER 3)
        "33101", "33102", "33103",
        # Construction / logistics
        "73100", "73300", "73400",
        # Hospitality / childcare
        "63200", "63201", "42202",
    ],
}

# ─── PEQ Legacy (closed for new applications since 2025) ────────────────────
PEQ_LEGACY: Dict[str, Any] = {
    "id": "peq_legacy",
    "name": "Programme de l'expérience québécoise (PEQ) — Legacy",
    "official_url": "https://www.quebec.ca/en/immigration/permanent/skilled-workers",
    "status": "closed_for_new_applicants_2025",
    "streams": [
        {"id": "peq_grad", "name": "Quebec Graduate Stream", "status": "closed"},
        {"id": "peq_worker", "name": "Temporary Foreign Worker Stream", "status": "closed"},
    ],
    "notes": "Kept for legal/audit reference. Existing applications continue to be processed.",
}

# CAQ — Quebec's Certificate of Acceptance (issued to PSTQ-approved applicants)
CAQ_INFO: Dict[str, str] = {
    "id": "caq",
    "name": "Certificat d'acceptation du Québec (CAQ) for Permanent Selection",
    "issued_to": "PSTQ-approved applicants (next step toward federal IRCC PR)",
    "url": "https://www.quebec.ca/en/immigration/permanent/skilled-workers/quebec-selection-certificate",
}


def _is_regulated(code: str) -> bool:
    """Heuristic: occupations in regulated NOC ranges typically require Quebec authorization.

    Regulated in QC: 31xxx (healthcare physicians/nurses/etc),
                     30xxx (specialized senior leaders),
                     21300-21399 (engineers),
                     41100 (lawyers),
                     32xxx (some allied health).
    """
    if not code or len(code) < 2:
        return False
    prefix2 = code[:2]
    prefix3 = code[:3]
    if prefix2 in {"31", "30", "32"}:
        return True
    if prefix3 in {"213", "411"}:  # engineers + lawyers
        return True
    return False


def _build_eligibility(code: str, teer: int) -> Dict[str, Any]:
    """Compute Quebec-specific eligibility payload for a single NOC code."""
    # Section eligibility based on FEER
    eligible_sections: List[Dict[str, Any]] = []
    for section in PSTQ_PROGRAM["sections"]:
        if teer in section["feer_eligible"]:
            # Special handling: Section C is for regulated only — skip if not regulated
            if section["id"] == "pstq_c" and not _is_regulated(code):
                continue
            eligible_sections.append({
                "section_id": section["id"],
                "name": section["name"],
                "french_required": section["french_required"],
                "priority": (
                    code in PSTQ_PROGRAM["priority_nocs_section_a"] if section["id"] == "pstq_a"
                    else code in PSTQ_PROGRAM["priority_nocs_section_b"] if section["id"] == "pstq_b"
                    else False
                ),
            })

    # Overall eligible flag
    eligible = len(eligible_sections) > 0

    return {
        "eligible": eligible,
        "feer_category": teer,
        "is_regulated": _is_regulated(code),
        "sections": eligible_sections,
        "current_program": "PSTQ",
        "peq_legacy_status": "closed_for_new_applicants_2025",
        "caq_required": eligible,
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "version": "2026-H1",
    }


async def apply_to_db(db, dry_run: bool = True, actor: str = "system") -> Dict[str, Any]:
    """Tag every CA NOC with quebec_eligibility block. Idempotent."""
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc)

    total = 0
    updated = 0
    skipped_unchanged = 0
    section_counts: Dict[str, int] = {s["id"]: 0 for s in PSTQ_PROGRAM["sections"]}
    section_counts["regulated"] = 0
    section_counts["priority_a"] = 0
    section_counts["priority_b"] = 0

    async for d in coll.find(
        {"country_code": "CA"},
        {"_id": 0, "code": 1, "teer_category": 1, "quebec_eligibility": 1},
    ):
        total += 1
        code = d.get("code")
        teer = d.get("teer_category")
        if not code or teer is None:
            continue

        new_block = _build_eligibility(code, teer)
        existing = d.get("quebec_eligibility") or {}

        # Tally analytics for every record (even skipped/unchanged ones)
        for s in new_block["sections"]:
            section_counts[s["section_id"]] = section_counts.get(s["section_id"], 0) + 1
            if s.get("priority"):
                if s["section_id"] == "pstq_a":
                    section_counts["priority_a"] += 1
                elif s["section_id"] == "pstq_b":
                    section_counts["priority_b"] += 1
        if new_block["is_regulated"]:
            section_counts["regulated"] += 1

        compare_fields = ["eligible", "sections", "is_regulated"]
        unchanged = all(existing.get(f) == new_block[f] for f in compare_fields)
        if unchanged and existing.get("source") == SOURCE_NAME:
            skipped_unchanged += 1
            continue

        if not dry_run:
            await coll.update_one(
                {"country_code": "CA", "code": code},
                {"$set": {
                    "quebec_eligibility": {**new_block, "last_synced_at": now},
                    "updated_at": now,
                }},
            )
        updated += 1

    # Store kb_settings singleton
    if not dry_run:
        await db["kb_settings"].replace_one(
            {"_id": "quebec_immigration"},
            {
                "_id": "quebec_immigration",
                "source": SOURCE_NAME,
                "version": "2026-H1",
                "pstq": PSTQ_PROGRAM,
                "peq_legacy": PEQ_LEGACY,
                "caq": CAQ_INFO,
                "updated_at": now,
            },
            upsert=True,
        )

    return {
        "source": SOURCE_NAME,
        "dry_run": dry_run,
        "version": "2026-H1",
        "active_program": "PSTQ",
        "peq_status": "closed_2025",
        "totals": {
            "ca_codes_processed": total,
            "sections_distribution": section_counts,
            "priority_a_codes": len(PSTQ_PROGRAM["priority_nocs_section_a"]),
            "priority_b_codes": len(PSTQ_PROGRAM["priority_nocs_section_b"]),
        },
        "counts": {"updated": updated, "skipped_unchanged": skipped_unchanged},
        "ran_at": now.isoformat(),
        "actor": actor,
    }
