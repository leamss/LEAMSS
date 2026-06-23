"""Option 1 / Z2 — Performance Benchmark Suite.

Asserts p95 latency budgets on critical endpoints. Run via:
    pytest backend/tests/perf/ -v

Optional baseline export:
    pytest backend/tests/perf/ --benchmark-json=/app/memory/perf_baseline_2026_06_20.json
    (requires pytest-benchmark; this suite degrades gracefully without it)

Budgets are 95th-percentile wall-clock measurements for a SINGLE call,
measured against the running backend at REACT_APP_BACKEND_URL.
"""
from __future__ import annotations

import os
import statistics
import time
from typing import Tuple

import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
if not API.endswith("/api"):
    API = API.rstrip("/") + "/api"

# Each tuple: (label, runs, budget_ms)
PERF_BUDGETS = {
    "funnel_metrics": 500,
    "coupons_list": 200,
    "coupon_validate": 200,
    "client_portal_overview": 400,
    "atlas_state_page": 250,
    "public_atlas_au_states": 250,
    "lead_capture": 300,
    "funnel_metrics_365d": 800,
}

ITERATIONS = 5  # 5 calls per endpoint; p95 estimated as max of N=5 (conservative)


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "admin@leamss.com", "password": "Admin@123"},
                      timeout=15)
    return r.json()["token"]


def _measure(callable_, runs: int = ITERATIONS) -> Tuple[float, float, float]:
    """Returns (p95_ms, mean_ms, max_ms). p95 ≈ max of N=5 (conservative)."""
    timings = []
    for _ in range(runs):
        t0 = time.perf_counter()
        callable_()
        timings.append((time.perf_counter() - t0) * 1000)
    timings.sort()
    return timings[-1], statistics.mean(timings), max(timings)


def test_perf_funnel_metrics_30d(admin_token):
    hdr = {"Authorization": f"Bearer {admin_token}"}
    p95, mean, mx = _measure(lambda: requests.get(
        f"{API}/admin/funnel-metrics?days=30", headers=hdr, timeout=5))
    assert p95 < PERF_BUDGETS["funnel_metrics"], \
        f"Funnel-30d p95={p95:.0f}ms exceeded budget {PERF_BUDGETS['funnel_metrics']}ms (mean={mean:.0f}ms)"


def test_perf_funnel_metrics_365d(admin_token):
    hdr = {"Authorization": f"Bearer {admin_token}"}
    p95, mean, mx = _measure(lambda: requests.get(
        f"{API}/admin/funnel-metrics?days=365", headers=hdr, timeout=5))
    assert p95 < PERF_BUDGETS["funnel_metrics_365d"], \
        f"Funnel-365d p95={p95:.0f}ms exceeded budget {PERF_BUDGETS['funnel_metrics_365d']}ms (mean={mean:.0f}ms)"


def test_perf_coupons_list(admin_token):
    hdr = {"Authorization": f"Bearer {admin_token}"}
    p95, mean, mx = _measure(lambda: requests.get(
        f"{API}/coupons", headers=hdr, timeout=5))
    assert p95 < PERF_BUDGETS["coupons_list"], \
        f"Coupons list p95={p95:.0f}ms exceeded budget {PERF_BUDGETS['coupons_list']}ms"


def test_perf_coupon_validate(admin_token):
    hdr = {"Authorization": f"Bearer {admin_token}"}
    p95, mean, mx = _measure(lambda: requests.get(
        f"{API}/coupons/validate?code=LUMPSUM20&order_value_inr=100000",
        headers=hdr, timeout=5))
    assert p95 < PERF_BUDGETS["coupon_validate"], \
        f"Coupon validate p95={p95:.0f}ms exceeded budget {PERF_BUDGETS['coupon_validate']}ms"


def test_perf_public_atlas_au_states():
    p95, mean, mx = _measure(lambda: requests.get(
        f"{API}/public-atlas/AU/states", timeout=5))
    assert p95 < PERF_BUDGETS["public_atlas_au_states"], \
        f"AU states list p95={p95:.0f}ms exceeded budget {PERF_BUDGETS['public_atlas_au_states']}ms"


def test_perf_lead_capture():
    """Lead POST should be sub-300ms (DB insert + audit + tag)."""
    import uuid
    p95, mean, mx = _measure(lambda: requests.post(
        f"{API}/public-atlas/lead",
        json={"name": "Perf Test", "email": f"perf.{uuid.uuid4().hex[:6]}@x.com",
              "phone": "+91 99999 11111", "country_of_interest": "AU",
              "interested_state": "NSW", "source": "perf_test"},
        timeout=5))
    assert p95 < PERF_BUDGETS["lead_capture"], \
        f"Lead capture p95={p95:.0f}ms exceeded budget {PERF_BUDGETS['lead_capture']}ms"


def test_perf_report_to_memory(admin_token):
    """Generate a one-shot perf snapshot saved to /tmp/perf_snapshot.json."""
    import json
    from datetime import datetime, timezone
    hdr = {"Authorization": f"Bearer {admin_token}"}

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "iterations_per_endpoint": ITERATIONS,
        "measurements": {},
    }
    endpoints = [
        ("funnel_30d", lambda: requests.get(f"{API}/admin/funnel-metrics?days=30", headers=hdr, timeout=5)),
        ("funnel_365d", lambda: requests.get(f"{API}/admin/funnel-metrics?days=365", headers=hdr, timeout=5)),
        ("coupons_list", lambda: requests.get(f"{API}/coupons", headers=hdr, timeout=5)),
        ("coupon_validate", lambda: requests.get(
            f"{API}/coupons/validate?code=LUMPSUM20&order_value_inr=100000", headers=hdr, timeout=5)),
        ("au_states_list", lambda: requests.get(f"{API}/public-atlas/AU/states", timeout=5)),
        ("au_state_nsw", lambda: requests.get(f"{API}/public-atlas/AU/state/NSW", timeout=5)),
    ]
    for label, fn in endpoints:
        p95, mean, mx = _measure(fn)
        snapshot["measurements"][label] = {
            "p95_ms": round(p95, 1), "mean_ms": round(mean, 1), "max_ms": round(mx, 1)
        }
    with open("/tmp/perf_snapshot.json", "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"\n[Z2 Perf] Snapshot saved to /tmp/perf_snapshot.json")
    print(json.dumps(snapshot["measurements"], indent=2))
    assert True  # always passes; reporting test
