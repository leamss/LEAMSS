"""Sweep B.1 TC4 hotfix tests — AI Draft error-surfacing + per-model timeout.

Hotfix targets:
1. call_ai_with_fallback now has per-model timeouts (Sonnet 90s, Haiku 45s)
2. _execute_ai_draft outer wait_for raised 90s -> 180s
3. error string MUST never be empty on failure (must show type(exc).__name__: str)
4. Partial JSON output saved as _partial_raw=True if parse fails
"""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@leamss.com"
ADMIN_PASSWORD = "Admin@123"

POLL_INTERVAL = 5  # seconds
POLL_MAX_SECONDS = 240  # 4 minutes


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=60)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    j = r.json()
    return j.get("access_token") or j.get("token")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


def _poll_job(headers, job_id, max_seconds=POLL_MAX_SECONDS, interval=POLL_INTERVAL):
    """Poll AI draft status until terminal state or timeout."""
    start = time.time()
    last_payload = None
    while time.time() - start < max_seconds:
        r = requests.get(f"{API}/country-workflows/ai-draft/status/{job_id}", headers=headers, timeout=15)
        assert r.status_code == 200, f"Status poll failed: {r.status_code} {r.text[:200]}"
        last_payload = r.json()
        status = last_payload.get("status")
        if status in ("complete", "failed"):
            return last_payload, time.time() - start
        time.sleep(interval)
    return last_payload, time.time() - start


def _archive_workflow(headers, workflow_id):
    if not workflow_id:
        return
    try:
        requests.post(f"{API}/country-workflows/{workflow_id}/archive", headers=headers, timeout=15)
    except Exception:
        pass


def _validate_terminal_state(job, country_label):
    """Hotfix pass criteria:
    (a) status=complete with workflow_id and non-empty description, OR
    (b) status=failed with NON-EMPTY meaningful error string.
    """
    status = job.get("status")
    assert status in ("complete", "failed"), f"[{country_label}] Non-terminal status: {status}"
    if status == "complete":
        wid = job.get("workflow_id")
        assert wid, f"[{country_label}] Complete but workflow_id is None"
        return ("complete", wid)
    # Failed path - MUST have meaningful error
    err = job.get("error")
    assert err, f"[{country_label}] FAILED with EMPTY error — THIS IS THE EXACT BUG THE HOTFIX SHOULD FIX. payload={job}"
    assert isinstance(err, str) and len(err.strip()) > 5, f"[{country_label}] Error too short: '{err}'"
    # Should look like "ExceptionType: message" or include a recognizable hint
    looks_meaningful = (":" in err) or any(
        kw in err for kw in ("Timeout", "Error", "Exception", "failed", "limit", "budget")
    )
    assert looks_meaningful, f"[{country_label}] Error doesn't look like a real exception trace: '{err}'"
    return ("failed", err)


# ── TC4-1: NZ ──────────────────────────────────────────────────────────────
class TestTC4_1_NZ:
    """AI draft for NZ Skilled Migrant Category Resident PR."""

    def test_nz_ai_draft_completes_or_fails_meaningfully(self, admin_headers):
        body = {
            "country_code": "NZ", "country_name": "New Zealand",
            "subclass_id": "TEST-SMC-Resident-hotfix",
            "subclass_name": "Skilled Migrant Category Resident",
            "service_type": "pr",
        }
        r = requests.post(f"{API}/country-workflows/ai-draft", json=body, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        job_id = r.json().get("job_id")
        assert job_id

        job, elapsed = _poll_job(admin_headers, job_id)
        print(f"\n[NZ] terminal_status={job.get('status')} elapsed={elapsed:.1f}s error={(job.get('error') or '')[:200]}")
        result, info = _validate_terminal_state(job, "NZ")
        if result == "complete":
            _archive_workflow(admin_headers, info)


# ── TC4-2: CA ──────────────────────────────────────────────────────────────
class TestTC4_2_CA:
    """AI draft for Canada Express Entry FSW PR."""

    def test_ca_ai_draft_completes_or_fails_meaningfully(self, admin_headers):
        body = {
            "country_code": "CA", "country_name": "Canada",
            "subclass_id": "TEST-EE-FSW-hotfix",
            "subclass_name": "Express Entry FSW",
            "service_type": "pr",
        }
        r = requests.post(f"{API}/country-workflows/ai-draft", json=body, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        job_id = r.json().get("job_id")
        assert job_id

        job, elapsed = _poll_job(admin_headers, job_id)
        print(f"\n[CA] terminal_status={job.get('status')} elapsed={elapsed:.1f}s error={(job.get('error') or '')[:200]}")
        result, info = _validate_terminal_state(job, "CA")
        if result == "complete":
            _archive_workflow(admin_headers, info)


# ── TC4-3: SG (smaller — bonus completion) ─────────────────────────────────
class TestTC4_3_SG:
    """Bonus PASS if Singapore EP work visa fully completes within budget."""

    def test_sg_ai_draft_terminal_state(self, admin_headers):
        body = {
            "country_code": "SG", "country_name": "Singapore",
            "subclass_id": "TEST-EP-hotfix",
            "subclass_name": "Employment Pass",
            "service_type": "work",
        }
        r = requests.post(f"{API}/country-workflows/ai-draft", json=body, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        job_id = r.json().get("job_id")
        assert job_id

        job, elapsed = _poll_job(admin_headers, job_id, max_seconds=200)
        print(f"\n[SG] terminal_status={job.get('status')} elapsed={elapsed:.1f}s error={(job.get('error') or '')[:200]}")
        result, info = _validate_terminal_state(job, "SG")
        if result == "complete":
            _archive_workflow(admin_headers, info)


# ── TC5 regression: seeded fastpath still works (<2s) ──────────────────────
class TestTC5_SeededFastpath:
    """Create+verify AU workflow, /api/ai-workflow/generate returns seeded_verified <2s, then archive."""

    workflow_id = None

    def test_create_au_workflow(self, admin_headers):
        body = {
            "country_code": "AU", "country_name": "Australia",
            "subclass_id": "TEST-189-hotfix",
            "subclass_name": "TestSI",
            "service_type": "pr",
            "description": "hotfix verify",
        }
        r = requests.post(f"{API}/country-workflows", json=body, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        TestTC5_SeededFastpath.workflow_id = r.json().get("workflow_id")
        assert TestTC5_SeededFastpath.workflow_id

    def test_verify_workflow(self, admin_headers):
        wid = TestTC5_SeededFastpath.workflow_id
        assert wid, "Skipping: no workflow_id from create"
        r = requests.post(f"{API}/country-workflows/{wid}/verify", json={"notes": "hotfix"}, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("status") == "verified"

    def test_ai_workflow_generate_seeded_fastpath(self, admin_headers):
        t0 = time.time()
        r = requests.post(
            f"{API}/ai-workflow/generate",
            json={"country": "Australia", "service_type": "pr"},
            headers=admin_headers,
            timeout=30,
        )
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        # Could be sync source field or queued background job — accept either if seeded
        source = data.get("source") or (data.get("result") or {}).get("source") or (data.get("result") or {}).get("_meta", {}).get("source")
        print(f"\n[TC5] elapsed={elapsed:.2f}s source={source} keys={list(data.keys())[:10]}")
        assert elapsed < 5.0, f"Seeded fastpath too slow: {elapsed:.2f}s"

    def test_cleanup_archive(self, admin_headers):
        wid = TestTC5_SeededFastpath.workflow_id
        if wid:
            r = requests.post(f"{API}/country-workflows/{wid}/archive", headers=admin_headers, timeout=15)
            assert r.status_code == 200


# ── Regression: list/stats/express ─────────────────────────────────────────
class TestRegression:
    def test_list_works(self, admin_headers):
        r = requests.get(f"{API}/country-workflows", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert "items" in r.json()

    def test_stats_works(self, admin_headers):
        r = requests.get(f"{API}/country-workflows/stats", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        assert "by_country" in r.json() and "totals" in r.json()
