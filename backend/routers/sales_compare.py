"""Phase 18.5 — Sales Compare Mode.

`POST /api/sales/compare`  — body `{codes: [{country_code, code}, ...]}` max 3.

Returns side-by-side comparison data + a deterministic narrative summary.
Auth: sales_rep / case_manager / admin / partner.
Cache: lightweight in-memory cache keyed on the sorted (cc,code) tuple, TTL 60s.
"""
from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/sales", tags=["sales-compare"])

OCCUPATION_MASTER = db["occupation_master"]

_ALLOWED_ROLES = {"sales_rep", "case_manager", "admin", "admin_owner", "partner"}


def _can_compare(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in _ALLOWED_ROLES or "*" in (user.get("permissions") or [])


class CompareCode(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=3)
    code: str = Field(..., min_length=1, max_length=20)


class CompareRequest(BaseModel):
    codes: List[CompareCode] = Field(..., min_length=1, max_length=3)


# In-process cache: {key: (expires_at_epoch, payload)}
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_TTL = 60


def _cache_key(codes: List[CompareCode]) -> str:
    pairs = sorted([(c.country_code.upper(), str(c.code)) for c in codes])
    return "|".join(f"{cc}-{code}" for cc, code in pairs)


def _outcome_distribution(cases: List[dict]) -> Dict[str, int]:
    dist = {"approved": 0, "refused": 0, "withdrawn": 0, "pending": 0}
    for c in cases or []:
        o = (c.get("outcome") or "").strip().lower()
        if o.startswith("approv"):
            dist["approved"] += 1
        elif o.startswith("refus"):
            dist["refused"] += 1
        elif o.startswith("withdr"):
            dist["withdrawn"] += 1
        elif o.startswith("pend"):
            dist["pending"] += 1
    return dist


def _days_since(iso_or_dt: Any) -> int | None:
    if not iso_or_dt:
        return None
    if hasattr(iso_or_dt, "isoformat"):
        dt = iso_or_dt if iso_or_dt.tzinfo else iso_or_dt.replace(tzinfo=timezone.utc)
    else:
        try:
            dt = datetime.fromisoformat(str(iso_or_dt).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:  # noqa: BLE001
            return None
    return max(0, (datetime.now(timezone.utc) - dt).days)


def _shape_occupation(occ: dict) -> dict:
    aa = occ.get("assessing_authority") or {}
    rvs = occ.get("recommended_visa_subclass") or {}
    cc = (occ.get("country_code") or "").upper()
    recommended_sub = rvs.get(cc) or ""
    elig = (occ.get("visa_pathways") or {}).get("visa_eligibility") or []
    eligible_subs = sorted({(v.get("visa_subclass") or v.get("subclass") or "").strip()
                            for v in elig
                            if (v.get("eligible") is True) and (v.get("visa_subclass") or v.get("subclass"))})
    docs = occ.get("required_documents") or []
    # category counts (sorted by count desc, top 3 names)
    cat_counts: Dict[str, int] = {}
    for d in docs:
        c = d.get("category") or "Other"
        cat_counts[c] = cat_counts.get(c, 0) + 1
    top_cats = [c for c, _ in sorted(cat_counts.items(), key=lambda x: -x[1])[:3]]
    ver = occ.get("verification") or {}
    return {
        "country_code": cc,
        "code": occ.get("code"),
        "title": occ.get("title") or "",
        "verification_meta": {
            "is_verified": bool(ver.get("is_verified")) or occ.get("status") == "verified",
            "verified_at": (ver.get("verified_at").isoformat() if hasattr(ver.get("verified_at"), "isoformat") else ver.get("verified_at")),
            "days_since_verified": _days_since(ver.get("verified_at")),
            "verified_by_name": ver.get("verified_by_name") or "",
        },
        "skill_body": ({
            "name": aa.get("name") or "",
            "processing_time_weeks": aa.get("processing_time_weeks"),
            "fee_native": aa.get("fee_native"),
            "fee_currency": aa.get("fee_currency") or "",
        } if aa.get("name") else None),
        "recommended_visa": ({
            "subclass": recommended_sub,
            "name": next((v.get("visa_name") for v in elig if (v.get("visa_subclass") or v.get("subclass")) == recommended_sub), recommended_sub),
        } if recommended_sub else None),
        "eligible_visas": eligible_subs,
        "required_documents_total": len(docs),
        "doc_categories_top3": top_cats,
        "similar_count": len(occ.get("similar_codes_override") or []),  # admin-pinned signal
        "similar_top2": (occ.get("similar_codes_override") or [])[:2],
        "sample_cases_count": len(occ.get("sample_cases") or []),
        "outcome_distribution": _outcome_distribution(occ.get("sample_cases") or []),
    }


def _build_narrative(occupations: List[dict]) -> str:
    """Deterministic comparison narrative. Skip empty signals gracefully."""
    if not occupations:
        return ""
    if len(occupations) == 1:
        o = occupations[0]
        return f"{o['code']} ({o['title']}) shown alone — pin another occupation to enable side-by-side analytics."

    parts: List[str] = []

    # 1. Common eligible visa subclasses
    common_subs = set(occupations[0].get("eligible_visas") or [])
    for o in occupations[1:]:
        common_subs &= set(o.get("eligible_visas") or [])
    if common_subs:
        plural = "subclasses" if len(common_subs) > 1 else "subclass"
        parts.append(f"All {len(occupations)} occupations qualify for {plural} {', '.join(sorted(common_subs))}.")
    else:
        parts.append(f"No common visa subclass — each occupation targets distinct pathways.")

    # 2. Shortest processing time among those with skill_body data
    with_time = [(o, (o.get("skill_body") or {}).get("processing_time_weeks"))
                 for o in occupations
                 if o.get("skill_body") and (o.get("skill_body") or {}).get("processing_time_weeks") is not None]
    if with_time:
        shortest = min(with_time, key=lambda x: x[1])
        body = (shortest[0].get("skill_body") or {}).get("name") or "the assessing body"
        parts.append(f"{shortest[0]['code']} has the shortest assessment timeline ({shortest[1]} weeks via {body}).")

    # 3. Recommended-visa highlight
    recs = [(o["code"], (o.get("recommended_visa") or {}).get("subclass"))
            for o in occupations
            if (o.get("recommended_visa") or {}).get("subclass")]
    if recs:
        parts.append(
            "Recommended primary pathway: "
            + ", ".join(f"{c} → {s}" for c, s in recs) + "."
        )

    # 4. Sample case count comparison
    with_cases = [(o["code"], o.get("sample_cases_count") or 0) for o in occupations]
    leader = max(with_cases, key=lambda x: x[1])
    if leader[1] > 0:
        parts.append(f"{leader[0]} has the most published sample cases ({leader[1]}) — best historical evidence.")

    # 5. Verification freshness
    fresh_pairs = [(o["code"], (o.get("verification_meta") or {}).get("days_since_verified"))
                   for o in occupations
                   if (o.get("verification_meta") or {}).get("days_since_verified") is not None]
    if fresh_pairs:
        freshest = min(fresh_pairs, key=lambda x: x[1])
        parts.append(f"{freshest[0]} was last verified {freshest[1]} day{'s' if freshest[1] != 1 else ''} ago — newest data on file.")

    return " ".join(parts)


@router.post("/compare")
async def compare_occupations(req: CompareRequest, current_user: dict = Depends(get_current_user)):
    if not _can_compare(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not req.codes:
        raise HTTPException(status_code=400, detail="Provide 1–3 occupation codes")
    if len(req.codes) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 occupations may be compared at once")

    key = _cache_key(req.codes)
    now_ts = time.time()
    if key in _CACHE:
        exp, payload = _CACHE[key]
        if exp > now_ts:
            return payload

    occupations: List[dict] = []
    not_found: List[Dict[str, str]] = []
    for c in req.codes:
        cc = c.country_code.upper()
        occ = await OCCUPATION_MASTER.find_one(
            {"country_code": cc, "code": str(c.code), "status": {"$ne": "superseded"}},
            {"_id": 0},
        )
        if not occ:
            not_found.append({"country_code": cc, "code": str(c.code)})
            continue
        occupations.append(_shape_occupation(occ))

    payload = {
        "occupations": occupations,
        "not_found": not_found,
        "summary_narrative": _build_narrative(occupations),
        "compared_at": datetime.now(timezone.utc).isoformat(),
    }
    _CACHE[key] = (now_ts + _TTL, payload)
    return payload



# ─────────────────────────────────────────────────────────────────────────────
# Phase 18.6 — Admin-only test hook to bust the in-process 60s cache.
# Cache lives in the FastAPI worker process; pytest can't reach it directly,
# so the regression suite hits this endpoint between modules to keep narrative
# assertions deterministic.
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/compare/_test/clear-cache")
async def clear_compare_cache_admin(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    role = (current_user.get("rbac_role") or current_user.get("role") or "").lower()
    if role not in {"admin", "admin_owner"}:
        raise HTTPException(status_code=403, detail="Admin only")
    n = len(_CACHE)
    _CACHE.clear()
    return {"status": "ok", "cleared": n}
