"""Phase 7.3.5 — Tier Auto-Advance Hook tests.

Tests the helper directly (idempotent, low-risk) + verifies the hook fires
end-to-end via the PA proposal-paid path.
"""
import os
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "https://career-match-320.preview.emergentagent.com"
BASE = f"{API}/api"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=10)
    return r.json()["token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# Direct helper tests (run async via asyncio)
def test_helper_upgrades_teaser_to_full(admin_headers):
    """Simulate PA stage transition to proposal_paid and verify snapshot upgraded."""
    import sys
    sys.path.insert(0, "/app/backend")
    from core.database import db
    from core.report_tier_hook import auto_upgrade_report_tiers_for_pa, TIER_RANK

    # Create assessment via API
    r = requests.post(f"{BASE}/sales/assessments", json={
        "client_name": "Tier Hook Test", "client_email": "tierhook@t.com", "client_phone": "+91-9000000400",
        "profile": {"marital_status": "single", "primary_applicant": {
            "personal": {"age": 30}, "education": {"highest_qualification": "master"},
            "language": {"scores": {"overall": 8, "listening": 8, "reading": 8, "writing": 7.5, "speaking": 8}},
            "professional": {"current_profession": "Software Engineer", "years_experience_total": 5},
            "au_extras": {}, "ca_extras": {}, "nz_extras": {},
        }},
        "occupation": {"country_code": "AU", "code": "261313", "title": "Software Engineer", "assessing_body": "ACS", "pathway": "MLTSSL"},
        "targets": [{"country": "AU", "visa_subclass": "189"}],
    }, headers=admin_headers, timeout=15)
    aid = r.json()["id"]

    # Generate report (default tier = teaser)
    g = requests.post(f"{BASE}/assessment-reports/generate", json={
        "assessment_id": aid, "persona": "client", "mode": "combined", "include_unverified": True,
    }, headers=admin_headers, timeout=30)
    snap_id = g.json()["snapshot_id"]

    # Manually insert a PA linking to this assessment (bypasses full PA creation flow)
    fake_pa_id = f"PA-TEST-{uuid.uuid4().hex[:8]}"
    asyncio.get_event_loop().run_until_complete(
        db["pre_assessments"].insert_one({
            "id": fake_pa_id,
            "assessment_id": aid,
            "client_name": "Tier Hook Test",
            "stage": "proposal_sent",
            "created_at": datetime.now(timezone.utc),
        })
    )

    try:
        # Fire the hook for proposal_paid
        result = asyncio.get_event_loop().run_until_complete(
            auto_upgrade_report_tiers_for_pa(fake_pa_id, "proposal_paid", payment_ref="TEST-001")
        )
        assert result["target_tier"] == "full"
        assert result["upgraded"] == 1
        assert result["skipped"] == 0

        # Verify snapshot now has full tier
        snap = asyncio.get_event_loop().run_until_complete(
            db["report_snapshots"].find_one({"snapshot_id": snap_id}, {"_id": 0})
        )
        assert snap["render_tier"] == "full"
        assert snap["tier_upgraded_by"] == "auto:pa_stage_hook"
        assert snap["tier_payment_ref"] == "TEST-001"

        # Idempotency: re-run should skip
        result2 = asyncio.get_event_loop().run_until_complete(
            auto_upgrade_report_tiers_for_pa(fake_pa_id, "proposal_paid")
        )
        assert result2["upgraded"] == 0
        assert result2["skipped"] == 1

        # Now upgrade to proposal tier via case_created
        result3 = asyncio.get_event_loop().run_until_complete(
            auto_upgrade_report_tiers_for_pa(fake_pa_id, "case_created", payment_ref="CASE-001")
        )
        assert result3["target_tier"] == "proposal"
        assert result3["upgraded"] == 1
        snap = asyncio.get_event_loop().run_until_complete(
            db["report_snapshots"].find_one({"snapshot_id": snap_id}, {"_id": 0})
        )
        assert snap["render_tier"] == "proposal"

        # No downgrade: setting back to proposal_paid should be no-op
        result4 = asyncio.get_event_loop().run_until_complete(
            auto_upgrade_report_tiers_for_pa(fake_pa_id, "proposal_paid")
        )
        assert result4["upgraded"] == 0
        assert result4["skipped"] == 1
        snap = asyncio.get_event_loop().run_until_complete(
            db["report_snapshots"].find_one({"snapshot_id": snap_id}, {"_id": 0})
        )
        assert snap["render_tier"] == "proposal"  # unchanged
    finally:
        # Cleanup
        asyncio.get_event_loop().run_until_complete(
            db["pre_assessments"].delete_one({"id": fake_pa_id})
        )
        requests.delete(f"{BASE}/sales/assessments/{aid}", headers=admin_headers)


def test_helper_no_op_for_irrelevant_stage(admin_headers):
    """Stages like 'under_review' or 'approved' should NOT upgrade tier."""
    import sys
    sys.path.insert(0, "/app/backend")
    from core.report_tier_hook import auto_upgrade_report_tiers_for_pa

    result = asyncio.get_event_loop().run_until_complete(
        auto_upgrade_report_tiers_for_pa("non-existent-pa", "under_review")
    )
    assert result["target_tier"] is None
    assert result["upgraded"] == 0


def test_helper_handles_missing_pa(admin_headers):
    import sys
    sys.path.insert(0, "/app/backend")
    from core.report_tier_hook import auto_upgrade_report_tiers_for_pa

    result = asyncio.get_event_loop().run_until_complete(
        auto_upgrade_report_tiers_for_pa("totally-fake-id", "proposal_paid")
    )
    assert result["upgraded"] == 0
    assert result.get("reason") == "pa_not_found"
