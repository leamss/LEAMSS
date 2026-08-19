"""Eligibility classification for the Bulk Pre-Assessment pipeline (Australia GSM).

Given a parsed client profile + computed points, decide which bucket the client
falls in so the report + email can be framed correctly:

    eligible        → 65+ points, age <= 44  (positive report — as before)
    improvable      → < 65 points, age <= 44  (not eligible YET; how to get there)
    ineligible_age  → age >= 45               (hard block for points-tested GSM)

Also produces human-readable reasons, improvement steps and alternatives that
render in both the PDF report and the client email.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

PASS_MARK = 65
AGE_CAP = 45  # 45+ at invitation = ineligible for 189/190/491 points test


def _best(points: Optional[Dict[str, Any]]) -> Tuple[str, int]:
    points = points or {}
    best_sc, best_pts = "189", 0
    for sc in ("189", "190", "491"):
        v = points.get(sc)
        if v is None:
            continue
        if int(v) >= best_pts:
            best_sc, best_pts = sc, int(v)
    return best_sc, best_pts


def _english_band(eng: Dict[str, Any]) -> str:
    """Rough IELTS-equivalent band label from the stored scores."""
    try:
        bands = [float(eng.get(b) or 0) for b in ("listening", "reading", "writing", "speaking")]
        overall = float(eng.get("overall") or 0)
    except (TypeError, ValueError):
        return "unknown"
    lo = min([b for b in bands if b > 0] or [overall])
    if lo >= 8.0:
        return "superior"      # +20
    if lo >= 7.0:
        return "proficient"    # +10
    if lo >= 6.0:
        return "competent"     # 0
    return "below_competent"


def _improvement_tips(parsed: Dict[str, Any], gap: int) -> List[str]:
    tips: List[str] = []
    eng = parsed.get("english") or {}
    band = _english_band(eng)
    if band in ("below_competent", "competent"):
        tips.append("Improve your English test score — reaching Proficient (IELTS 7 / PTE 65 each band) adds +10 points, "
                    "and Superior (IELTS 8 / PTE 79 each band) adds +20 points. This is usually the fastest way to gain points.")
    elif band == "proficient":
        tips.append("Push your English from Proficient to Superior (IELTS 8 / PTE 79 in every band) to gain an extra +10 points.")

    exp = parsed.get("experience_total")
    if exp is not None:
        try:
            exp = float(exp)
            if exp < 8:
                tips.append("Gaining more skilled work experience increases points — 3, 5 and 8 years of relevant overseas "
                            "experience unlock +5, +10 and +15 points respectively.")
        except (TypeError, ValueError):
            pass

    if not parsed.get("state_nominated"):
        tips.append("Apply for State/Territory nomination — Subclass 190 adds +5 points and Subclass 491 (regional) adds +15 points, "
                    "which alone can lift you above the pass mark.")

    marital = str(parsed.get("marital_status") or "").lower()
    if marital in ("married", "de_facto"):
        tips.append("If your partner completes a skills assessment (age under 45 + competent English) you can claim +10 partner points, "
                    "or +5 for partner competent English only.")

    extras = parsed.get("au_extras") or {}
    if not extras.get("professional_year_completed"):
        tips.append("Completing a Professional Year in Australia (accounting, IT or engineering) adds +5 points.")
    if not extras.get("naati_accredited"):
        tips.append("A NAATI Credentialled Community Language (CCL) test pass adds +5 points.")
    if not extras.get("australian_study_2_years"):
        tips.append("An eligible 2-year Australian study qualification adds +5 points (plus regional/STEM study bonuses).")

    tips.append(f"You need {gap} more point(s). Combining any two of the above steps will usually be enough to cross the "
                f"{PASS_MARK}-point mark and become invitable.")
    return tips


def classify_eligibility(parsed: Dict[str, Any], points: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the eligibility verdict block for a client."""
    age = parsed.get("age")
    best_sc, best_pts = _best(points)

    # ── Hard block: age 45+ ──────────────────────────────────────────
    if age is not None and int(age) >= AGE_CAP:
        return {
            "verdict": "ineligible_age",
            "eligible": False,
            "best_subclass": best_sc,
            "best_points": best_pts,
            "pass_mark": PASS_MARK,
            "headline": "Not Eligible for General Skilled Migration",
            "sub": "Based on the age criteria for Australia's points-tested skilled visas",
            "reasons": [
                f"Age {int(age)}: Australia's General Skilled Migration (Subclass 189 / 190 / 491) has a strict upper age "
                f"limit — applicants who are {AGE_CAP} or older at the time of invitation cannot be awarded age points and "
                f"are not eligible for these points-tested visas.",
            ],
            "improvements": [],
            "alternatives": [
                "Employer-Sponsored pathways (Subclass 482 TSS / 186 ENS / 494 regional) — these are not points-tested and "
                "may have different age considerations where an Australian employer sponsors you.",
                "Global Talent or Business & Investment streams, if your profile fits.",
                "Nominating a skilled family member (spouse/partner under 45) as the primary applicant, with you included "
                "as the accompanying partner.",
            ],
        }

    # ── Eligible ─────────────────────────────────────────────────────
    if best_pts >= PASS_MARK:
        return {
            "verdict": "eligible",
            "eligible": True,
            "best_subclass": best_sc,
            "best_points": best_pts,
            "pass_mark": PASS_MARK,
            "headline": "You Meet the Eligibility Threshold",
            "sub": f"{best_pts} points on your best pathway (Subclass {best_sc}) — at or above the {PASS_MARK}-point pass mark",
            "reasons": [],
            "improvements": [],
            "alternatives": [],
        }

    # ── Improvable (not eligible yet, age under 45) ──────────────────
    gap = PASS_MARK - best_pts
    return {
        "verdict": "improvable",
        "eligible": False,
        "best_subclass": best_sc,
        "best_points": best_pts,
        "pass_mark": PASS_MARK,
        "headline": "Not Eligible Yet — But Within Reach",
        "sub": f"You are {gap} point(s) short of the {PASS_MARK}-point mark. With the right steps, you may qualify in the future.",
        "reasons": [
            f"Your current indicative score is {best_pts} points on your best pathway (Subclass {best_sc}), which is "
            f"{gap} point(s) below the minimum of {PASS_MARK} points required to receive an invitation to apply.",
        ],
        "improvements": _improvement_tips(parsed, gap),
        "alternatives": [],
    }


def manual_verdict(kind: str, reason: str, parsed: Dict[str, Any], points: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build an eligibility block from a consultant's MANUAL override.

    kind: 'improvable'  → Not eligible now, but possible in the future
          'ineligible'  → Not eligible (permanent / hard block, e.g. documents)
    reason: the consultant's own explanation (shown as the primary reason).
    """
    best_sc, best_pts = _best(points)
    reason = (reason or "").strip()
    if kind == "improvable":
        return {
            "verdict": "improvable", "eligible": False, "manual": True,
            "best_subclass": best_sc, "best_points": best_pts, "pass_mark": PASS_MARK,
            "headline": "Not Eligible Yet — But Possible in the Future",
            "sub": "Based on our review of your profile and documents",
            "reasons": [reason] if reason else
                       [f"Based on our detailed review, your profile does not currently meet the {PASS_MARK}-point "
                        f"requirement for an invitation."],
            "improvements": _improvement_tips(parsed, max(PASS_MARK - best_pts, 5)),
            "alternatives": [],
        }
    return {
        "verdict": "ineligible", "eligible": False, "manual": True,
        "best_subclass": best_sc, "best_points": best_pts, "pass_mark": PASS_MARK,
        "headline": "Not Eligible for General Skilled Migration",
        "sub": "Based on our review of your profile and documents",
        "reasons": [reason] if reason else
                   ["Based on the documents and information reviewed, your profile does not meet the current "
                    "eligibility requirements for the points-tested skilled visas."],
        "improvements": [],
        "alternatives": [
            "Employer-Sponsored pathways (Subclass 482 TSS / 186 ENS / 494 regional) where an Australian employer sponsors you.",
            "Other visa categories that may suit your profile — our migration team will be glad to advise you.",
        ],
    }


def bucket_for_row(row: Dict[str, Any]) -> str:
    """Classify a bulk row into an actionable bucket for the email UI.

    Returns one of: eligible | improvable | ineligible | needs_resume
    """
    status = row.get("status")
    if status in ("needs_ai", "error"):
        return "needs_resume"
    ev = row.get("eligibility") or {}
    verdict = ev.get("verdict")
    if verdict == "eligible":
        return "eligible"
    if verdict == "improvable":
        return "improvable"
    if verdict in ("ineligible_age", "ineligible"):
        return "ineligible"
    # generated but no verdict computed yet → treat by points
    return "eligible"
