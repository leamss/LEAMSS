"""Phase 7.5 — Pipeline Cockpit Router.

Single-pane API that unifies LEAMSS pipeline records across collections:

  • leads               → `leads`
  • assessments         → `sales_assessments` (no linked PA yet)
  • pre-assessments     → `pre_assessments` in early stages
  • proposals           → `pre_assessments` in proposal_sent
  • cases               → `pre_assessments` in proposal_paid / case_created
  • closed              → `pre_assessments` in rejected / refunded

Endpoints:
  GET /api/cockpit/funnel  — live counts per stage
  GET /api/cockpit/cards   — paginated card list with filters
  GET /api/cockpit/brief   — AI Brief stats for sidebar
  GET /api/cockpit/card/{type}/{id} — drill-in detail
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/cockpit", tags=["Cockpit"])

# ─── Stage taxonomy ──────────────────────────────────────────────────────────
STAGE_KEYS = ["leads", "assessments", "pa", "proposals", "cases", "closed"]

PA_STAGE_GROUPS = {
    "pa": {"new", "payment_pending", "payment_received", "documents_submitted",
           "under_review", "approved", "express_pending_approval"},
    "proposals": {"proposal_sent"},
    "cases": {"proposal_paid", "awaiting_final_approval", "case_created"},
    "closed": {"rejected", "refunded", "express_rejected"},
}

# Maps PA stage → next-action label + urgency
PA_NEXT_ACTION = {
    "new":                       ("Send Payment Link", "high"),
    "payment_pending":           ("Awaiting PA Fee Payment", "medium"),
    "payment_received":          ("Submit Documents", "high"),
    "documents_submitted":       ("Awaiting Admin Review", "medium"),
    "under_review":              ("Admin Reviewing", "low"),
    "approved":                  ("Send Sales Proposal", "high"),
    "proposal_sent":             ("Awaiting Main Fee Payment", "medium"),
    "proposal_paid":             ("Create Case", "high"),
    "awaiting_final_approval":   ("Final Approval Pending", "medium"),
    "case_created":              ("Case Active — Documentation", "low"),
    "rejected":                  ("Refund Initiated", "low"),
    "refunded":                  ("Closed — Refunded", "low"),
    "express_pending_approval":  ("Express PA Awaiting Approval", "high"),
    "express_rejected":          ("Express Rejected", "low"),
}

LIFECYCLE_FROM_PA_STAGE = {
    "new": 3, "payment_pending": 3, "express_pending_approval": 3,
    "payment_received": 4, "documents_submitted": 4, "under_review": 4,
    "approved": 4, "rejected": 4, "refunded": 4, "refund_initiated": 4,
    "express_rejected": 4, "proposal_sent": 4,
    "proposal_paid": 5, "awaiting_final_approval": 5,
    "case_created": 6,
}


# ─── Permissions ─────────────────────────────────────────────────────────────
def _is_admin(user: dict) -> bool:
    role = (user.get("role") or "").lower()
    return role in ("admin", "admin_owner", "case_manager") or "*" in (user.get("permissions") or [])


def _own_query(user: dict) -> Dict[str, Any]:
    """Returns the ownership filter for non-admin users."""
    if _is_admin(user):
        return {}
    return {"created_by": user["id"]}


def _own_pa_query(user: dict) -> Dict[str, Any]:
    """Ownership filter for PAs (uses partner_id field)."""
    if _is_admin(user):
        return {}
    return {"partner_id": user["id"]}


def _own_lead_query(user: dict) -> Dict[str, Any]:
    if _is_admin(user):
        return {}
    return {"assigned_to": user["id"]}


# ─── Card builders (per source) ──────────────────────────────────────────────
def _humanize_ago(dt: Optional[datetime]) -> str:
    if not dt:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    if secs < 60:        return "just now"
    if secs < 3600:      return f"{secs // 60} min ago"
    if secs < 86400:     return f"{secs // 3600} hr ago"
    if secs < 604800:    return f"{secs // 86400} day{'s' if secs // 86400 > 1 else ''} ago"
    return dt.strftime("%d %b %Y")


def _build_lead_card(d: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a `leads` doc into a cockpit card."""
    country = d.get("country_of_interest") or ""
    return {
        "id": d.get("id"),
        "type": "lead",
        "name": d.get("name") or "Unnamed Lead",
        "stage": "leads",
        "countries": [country] if country else [],
        "score": None,
        "score_label": d.get("service_interested") or "New enquiry",
        "lifecycle": 0,
        "next_action": "Start Eligibility Wizard",
        "urgency": d.get("priority") or "medium",
        "owner": {
            "id": d.get("assigned_to"),
            "name": d.get("assigned_to_name") or "Unassigned",
        },
        "updated_at": d.get("updated_at") or d.get("created_at"),
        "updated_at_human": _humanize_ago(d.get("updated_at") or d.get("created_at")),
        "source": d.get("source") or "website",
    }


def _build_assessment_card(d: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a `sales_assessments` (no PA yet) doc into a cockpit card."""
    best_cc = d.get("best_country_code") or ""
    best_total = d.get("best_total")
    has_report = bool(d.get("latest_report_snapshot_id"))
    next_action = "Generate Report" if not has_report else "Create Pre-Assessment"
    return {
        "id": d.get("id"),
        "type": "assessment",
        "name": d.get("client_name") or "Untitled",
        "stage": "assessments",
        "countries": [best_cc] if best_cc else [],
        "score": best_total,
        "score_label": (
            f"{best_cc} {best_total} pts" if best_cc and best_total is not None
            else "Calculating…"
        ),
        "lifecycle": 2 if has_report else (1 if best_total is not None else 0),
        "next_action": next_action,
        "urgency": "high" if not has_report else "medium",
        "owner": {
            "id": d.get("created_by"),
            "name": d.get("created_by_name") or "—",
        },
        "updated_at": d.get("updated_at") or d.get("created_at"),
        "updated_at_human": _humanize_ago(d.get("updated_at") or d.get("created_at")),
    }


def _build_pa_card(d: Dict[str, Any], stage_group: str) -> Dict[str, Any]:
    """Normalize a `pre_assessments` doc into a cockpit card."""
    pa_stage = d.get("stage") or "new"
    countries = [(d.get("target_country") or "").upper()] if d.get("target_country") else []
    next_action, urgency = PA_NEXT_ACTION.get(pa_stage, ("Review", "medium"))
    return {
        "id": d.get("id"),
        "type": "pa",
        "name": d.get("client_name") or "Untitled",
        "stage": stage_group,
        "countries": countries,
        "score": d.get("eligibility_score"),
        "score_label": (
            f"{d.get('pa_number') or d.get('id', '')[:8]} · {pa_stage.replace('_', ' ').title()}"
        ),
        "lifecycle": LIFECYCLE_FROM_PA_STAGE.get(pa_stage, 3),
        "next_action": next_action,
        "urgency": urgency,
        "owner": {
            "id": d.get("partner_id"),
            "name": d.get("partner_name") or "—",
        },
        "updated_at": d.get("updated_at") or d.get("created_at"),
        "updated_at_human": _humanize_ago(d.get("updated_at") or d.get("created_at")),
        "pa_stage": pa_stage,
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────
@router.get("/funnel")
async def get_funnel(current_user: dict = Depends(get_current_user)):
    """Live counts per stage. Respects ownership scoping."""
    leads_q = _own_lead_query(current_user) | {"stage": {"$ne": "converted"}}
    sa_q    = _own_query(current_user) | {"linked_pa_id": {"$in": [None, ""]}}
    pa_q    = _own_pa_query(current_user)

    leads_n = await db["leads"].count_documents(leads_q)
    assessments_n = await db["sales_assessments"].count_documents(sa_q)

    pa_counts = {k: 0 for k in ("pa", "proposals", "cases", "closed")}
    cursor = db["pre_assessments"].find(pa_q, {"_id": 0, "stage": 1})
    async for row in cursor:
        st = row.get("stage")
        for group, members in PA_STAGE_GROUPS.items():
            if st in members:
                pa_counts[group] += 1
                break

    return {
        "leads": leads_n,
        "assessments": assessments_n,
        "pa": pa_counts["pa"],
        "proposals": pa_counts["proposals"],
        "cases": pa_counts["cases"],
        "closed": pa_counts["closed"],
        "total_active": leads_n + assessments_n + pa_counts["pa"] + pa_counts["proposals"] + pa_counts["cases"],
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/cards")
async def get_cards(
    stage: Optional[str] = Query(None, description="leads|assessments|pa|proposals|cases|closed|all"),
    owner: Optional[str] = Query(None, description="me|all|<user_id>"),
    search: Optional[str] = Query(None),
    sort: str = Query("recent", description="recent|oldest|score_desc|score_asc"),
    limit: int = Query(60, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """Unified card list across leads, assessments, and PAs."""
    cards: List[Dict[str, Any]] = []
    is_admin = _is_admin(current_user)

    # Owner override
    if owner == "me" or (not is_admin and owner != "all"):
        own_filter_lead = {"assigned_to": current_user["id"]}
        own_filter_sa   = {"created_by":  current_user["id"]}
        own_filter_pa   = {"partner_id":  current_user["id"]}
    elif owner and owner not in ("all", "me"):
        own_filter_lead = {"assigned_to": owner}
        own_filter_sa   = {"created_by":  owner}
        own_filter_pa   = {"partner_id":  owner}
    else:
        own_filter_lead = own_filter_sa = own_filter_pa = {}

    text_re = {"$regex": search, "$options": "i"} if search else None

    want_all = (not stage) or stage == "all"

    # 1) Leads
    if want_all or stage == "leads":
        q = own_filter_lead | {"stage": {"$ne": "converted"}}
        if text_re:
            q["$or"] = [{"name": text_re}, {"email": text_re}, {"phone": text_re}]
        async for d in db["leads"].find(q, {"_id": 0}).sort("updated_at", -1).limit(limit):
            cards.append(_build_lead_card(d))

    # 2) Sales assessments (no PA yet)
    if want_all or stage == "assessments":
        q = own_filter_sa | {"linked_pa_id": {"$in": [None, ""]}}
        if text_re:
            q["client_name"] = text_re
        proj = {
            "_id": 0, "id": 1, "client_name": 1, "best_country_code": 1, "best_total": 1,
            "latest_report_snapshot_id": 1, "created_at": 1, "updated_at": 1,
            "created_by": 1, "created_by_name": 1,
        }
        async for d in db["sales_assessments"].find(q, proj).sort("updated_at", -1).limit(limit):
            cards.append(_build_assessment_card(d))

    # 3) Pre-assessments (grouped by stage)
    pa_stage_filter: Optional[Dict[str, Any]] = None
    if want_all:
        pa_stage_filter = {}
    elif stage in PA_STAGE_GROUPS:
        pa_stage_filter = {"stage": {"$in": list(PA_STAGE_GROUPS[stage])}}

    if pa_stage_filter is not None:
        q = own_filter_pa | pa_stage_filter
        if text_re:
            q["client_name"] = text_re
        proj = {
            "_id": 0, "id": 1, "pa_number": 1, "client_name": 1, "stage": 1,
            "target_country": 1, "eligibility_score": 1, "created_at": 1, "updated_at": 1,
            "partner_id": 1, "partner_name": 1,
        }
        async for d in db["pre_assessments"].find(q, proj).sort("updated_at", -1).limit(limit):
            st = d.get("stage")
            for group, members in PA_STAGE_GROUPS.items():
                if st in members:
                    cards.append(_build_pa_card(d, group))
                    break

    # Sort
    def _sort_key_recent(c):
        u = c.get("updated_at")
        if isinstance(u, str):
            try: u = datetime.fromisoformat(u.replace("Z", "+00:00"))
            except ValueError: u = None
        return u or datetime.min.replace(tzinfo=timezone.utc)

    if sort == "oldest":
        cards.sort(key=_sort_key_recent)
    elif sort == "score_desc":
        cards.sort(key=lambda c: c.get("score") or -1, reverse=True)
    elif sort == "score_asc":
        cards.sort(key=lambda c: c.get("score") or 999999)
    else:  # recent (default)
        cards.sort(key=_sort_key_recent, reverse=True)

    cards = cards[:limit]

    # Stringify datetime fields for JSON
    for c in cards:
        if isinstance(c.get("updated_at"), datetime):
            c["updated_at"] = c["updated_at"].isoformat()

    return {"items": cards, "count": len(cards), "as_of": datetime.now(timezone.utc).isoformat()}


@router.get("/brief")
async def get_ai_brief(current_user: dict = Depends(get_current_user)):
    """AI Brief panel — actionable stats for the right sidebar."""
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(hours=48)

    leads_q = _own_lead_query(current_user) | {
        "stage": {"$ne": "converted"},
        "$or": [{"last_contacted_at": None}, {"last_contacted_at": {"$lt": stale_cutoff}}],
    }
    stale_leads_n = await db["leads"].count_documents(leads_q)

    pa_q = _own_pa_query(current_user) | {"stage": "payment_pending"}
    payment_pending_n = await db["pre_assessments"].count_documents(pa_q)

    pa_q2 = _own_pa_query(current_user) | {"stage": "proposal_sent"}
    proposals_pending_n = await db["pre_assessments"].count_documents(pa_q2)

    verify_q = {"status": {"$in": ["draft", "unverified"]}}
    pending_verify_n = await db["country_templates"].count_documents(verify_q)

    insights = []
    if stale_leads_n:
        insights.append({
            "icon": "alert",
            "title": f"{stale_leads_n} leads not contacted in 48 hours",
            "cta_label": "Open Pre-Assessments",
            "cta_link": "/admin?tab=pre-assessments",
            "urgency": "high",
        })
    if payment_pending_n:
        insights.append({
            "icon": "clock",
            "title": f"{payment_pending_n} PA fee window closing soon",
            "cta_label": "Send Reminder",
            "cta_link": "/admin?tab=pre-assessments",
            "urgency": "medium",
        })
    if proposals_pending_n:
        insights.append({
            "icon": "mail",
            "title": f"{proposals_pending_n} proposals awaiting client decision",
            "cta_label": "Follow Up",
            "cta_link": "/admin?tab=pre-assessments",
            "urgency": "medium",
        })
    if pending_verify_n:
        insights.append({
            "icon": "shield",
            "title": f"{pending_verify_n} KB items awaiting verification",
            "cta_label": "Verify Hub",
            "cta_link": "/admin/verify-hub",
            "urgency": "low",
        })

    return {
        "insights": insights,
        "counts": {
            "stale_leads": stale_leads_n,
            "payment_pending": payment_pending_n,
            "proposals_pending": proposals_pending_n,
            "pending_verify": pending_verify_n,
        },
        "as_of": now.isoformat(),
    }


@router.get("/card/{kind}/{ref_id}")
async def get_card_detail(
    kind: str, ref_id: str, current_user: dict = Depends(get_current_user)
):
    """Drill-in detail for a single card."""
    if kind == "lead":
        d = await db["leads"].find_one({"id": ref_id}, {"_id": 0})
        if not d:
            raise HTTPException(status_code=404, detail="Lead not found")
        if not _is_admin(current_user) and d.get("assigned_to") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not your lead")
        return {
            "kind": "lead",
            "record": d,
            "lifecycle": [{"key": "lead_captured", "label": "Lead Captured",
                          "completed": True, "timestamp": d.get("created_at")}],
        }

    if kind == "assessment":
        d = await db["sales_assessments"].find_one({"id": ref_id}, {"_id": 0})
        if not d:
            raise HTTPException(status_code=404, detail="Assessment not found")
        if not _is_admin(current_user) and d.get("created_by") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not your assessment")
        # Reuse existing lifecycle endpoint logic — light copy
        return {"kind": "assessment", "record_id": d.get("id"),
                "name": d.get("client_name"),
                "best_country": d.get("best_country_code"),
                "best_total": d.get("best_total"),
                "latest_report_id": d.get("latest_report_snapshot_id"),
                "results_count": len(d.get("results") or []),
                "deep_link": f"/sales/client-assessment?id={d.get('id')}"}

    if kind == "pa":
        d = await db["pre_assessments"].find_one({"id": ref_id}, {"_id": 0})
        if not d:
            raise HTTPException(status_code=404, detail="Pre-Assessment not found")
        if not _is_admin(current_user) and d.get("partner_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not your pre-assessment")
        return {"kind": "pa", "record_id": d.get("id"),
                "pa_number": d.get("pa_number"),
                "name": d.get("client_name"),
                "stage": d.get("stage"),
                "deep_link": "/admin?tab=pre-assessments"}

    raise HTTPException(status_code=400, detail=f"Unknown kind: {kind}")
