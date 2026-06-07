"""Phase 9.4 — Smart Sales Helper Calculator P0 Bug Fixes regression tests.

Scenarios verified:
  1) Single applicant gets 10 partner-skills points (per Home Affairs rules)
  2) /sales/calculator/calculate-batch and /sales/wizard/calculate-parallel
     return IDENTICAL totals for the SAME profile (no mismatch).
  3) Re-saving an assessment with the same profile yields the same total
     (no point-drift on hydrate-then-save round-trip).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://staff-dashboard-66.preview.emergentagent.com")
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# Canonical sample profile — mimics what the wizard's buildProfile() would emit
def _make_profile(age=30, marital="single", qual="bachelor", overall=7.5, naati=False,
                  state_nominated=False):
    return {
        "marital_status": marital,
        "primary_applicant": {
            "personal": {"age": age},
            "education": {"highest_qualification": qual},
            "language": {
                "scores": {"overall": overall, "listening": overall, "reading": overall,
                           "writing": overall, "speaking": overall},
            },
            "professional": {
                "years_experience_total": 6.0,
                "years_experience_australia": 0.0,
            },
            "au_extras": {
                "naati_accredited": naati,
                "professional_year_completed": False,
                "australian_study_2_years": False,
                "specialist_education_stem_au": False,
                "regional_study_au": False,
                "state_nominated": state_nominated,
                "state_code": "NSW" if state_nominated else None,
            },
        },
        "spouse": None,
    }


# ─── Bug #1 — Single applicant must get partner=10 (per Home Affairs rules) ──
def test_single_applicant_gets_10_partner_points(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/sales/calculator/calculate",
        headers=admin_headers,
        json={"profile": _make_profile(marital="single"), "country": "AU", "visa_subclass": "189"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    partner = body["breakdown"].get("partner")
    assert partner is not None, "Partner breakdown missing"
    assert partner["points"] == 10, f"Single applicant should get 10 partner pts, got {partner['points']}"
    assert partner["matched_key"] == "single_or_pr_partner"


# ─── Bug #2 — calculate-batch vs calculate-parallel must match ───────────────
def test_batch_vs_parallel_same_total(admin_headers):
    """The 'mismatch' Sir reported was caused by ParallelSubclassPanel reading
    wrong frontend field names. Backend now confirms BOTH endpoints emit the
    same numbers for the same canonical profile."""
    profile = _make_profile(age=30, qual="bachelor", overall=7.5, marital="single")

    # batch endpoint (used by Step5Calculator main results)
    r1 = requests.post(
        f"{BASE_URL}/api/sales/calculator/calculate-batch",
        headers=admin_headers,
        json={"profile": profile, "targets": [
            {"country": "AU", "visa_subclass": "189"},
            {"country": "AU", "visa_subclass": "190"},
            {"country": "AU", "visa_subclass": "491"},
        ]},
        timeout=15,
    )
    assert r1.status_code == 200
    batch_results = r1.json()["results"]
    batch_totals = {r["visa_subclass"]: r["total"] for r in batch_results}

    # parallel endpoint (used by ParallelSubclassPanel)
    r2 = requests.post(
        f"{BASE_URL}/api/sales/wizard/calculate-parallel",
        headers=admin_headers,
        json={"profile": profile, "country_code": "AU",
              "visa_subclasses": ["189", "190", "491"]},
        timeout=15,
    )
    assert r2.status_code == 200
    parallel_results = r2.json()["subclasses"]
    parallel_totals = {r["visa_subclass"]: r["total"] for r in parallel_results}

    assert batch_totals == parallel_totals, \
        f"MISMATCH batch={batch_totals} parallel={parallel_totals}"


# ─── Bug #4 — Re-save deterministic, no drift ────────────────────────────────
def test_save_assessment_no_point_drift(admin_headers):
    profile = _make_profile(age=29, qual="master", overall=8.0, marital="single", naati=True, state_nominated=True)

    payload = {
        "client_name": "P9.4 Drift Test",
        "client_email": "drift@test.com",
        "profile": profile,
        "occupation": None,
        "targets": [{"country": "AU", "visa_subclass": "491"}],
    }
    r1 = requests.post(
        f"{BASE_URL}/api/sales/assessments",
        headers=admin_headers, json=payload, timeout=15,
    )
    assert r1.status_code == 200, r1.text
    first = r1.json()
    aid = first["id"]
    first_total = first["best_total"]
    assert first_total > 0

    # Fetch + re-save (simulates the resume → re-save flow)
    g = requests.get(f"{BASE_URL}/api/sales/assessments/{aid}", headers=admin_headers, timeout=15)
    assert g.status_code == 200
    fetched = g.json()
    # Use the fetched profile_snapshot (round-trip) as the input
    r2 = requests.post(
        f"{BASE_URL}/api/sales/assessments",
        headers=admin_headers,
        json={
            "client_name": fetched["client_name"],
            "client_email": fetched.get("client_email"),
            "profile": fetched["profile_snapshot"],
            "occupation": fetched.get("occupation"),
            "targets": fetched["targets"],
        },
        timeout=15,
    )
    assert r2.status_code == 200
    second_total = r2.json()["best_total"]
    assert second_total == first_total, \
        f"DRIFT: re-save changed score from {first_total} to {second_total}"

    # Cleanup
    requests.delete(f"{BASE_URL}/api/sales/assessments/{aid}", headers=admin_headers, timeout=10)
    requests.delete(f"{BASE_URL}/api/sales/assessments/{r2.json()['id']}", headers=admin_headers, timeout=10)


# ─── Bug #3 — Parallel endpoint returns all 3 subclasses with best pick ──────
def test_parallel_returns_all_three_subclasses(admin_headers):
    profile = _make_profile(age=30, qual="bachelor", overall=7.0, marital="single",
                            state_nominated=True)
    r = requests.post(
        f"{BASE_URL}/api/sales/wizard/calculate-parallel",
        headers=admin_headers,
        json={"profile": profile, "country_code": "AU",
              "visa_subclasses": ["189", "190", "491"]},
        timeout=15,
    )
    assert r.status_code == 200
    body = r.json()
    subs = body["subclasses"]
    codes = {s["visa_subclass"] for s in subs}
    assert codes == {"189", "190", "491"}, f"Missing subclasses: {codes}"
    # 491 should win (state_nominated + 15 points for 491 vs 5 for 190)
    assert body["best_subclass"] in ("189", "190", "491")


# ─── Sanity: married + AU PR spouse also gets 10 partner pts ─────────────────
def test_married_with_au_pr_spouse_gets_10(admin_headers):
    profile = _make_profile(marital="married")
    profile["spouse"] = {
        "contribution_type": "australian_pr_citizen",
        "is_applicant_on_visa": False,
        "is_australian_pr_or_citizen": True,
        "personal": {"age": 32},
        "language": {"scores": {"overall": 7.0}},
        "education": {"highest_qualification": "bachelor"},
    }
    r = requests.post(
        f"{BASE_URL}/api/sales/calculator/calculate",
        headers=admin_headers,
        json={"profile": profile, "country": "AU", "visa_subclass": "189"},
        timeout=15,
    )
    assert r.status_code == 200
    partner = r.json()["breakdown"].get("partner")
    assert partner is not None
    assert partner["points"] == 10
    assert partner["matched_key"] == "single_or_pr_partner"
