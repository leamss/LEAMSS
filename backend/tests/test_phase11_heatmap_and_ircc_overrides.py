"""Phase 11 — Per-country Field Coverage Heatmap (CA + NZ) + IRCC Category Overrides.

Two features under test:
  A) /api/anz-intel/audit-summary now returns field_coverage_ca + field_coverage_nz
  B) /api/anz-intel/audit-rows?country=CA|NZ uses country-specific tracked fields
  C) IRCC Category Overrides CRUD: GET/PUT/DELETE + reapply
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://compliance-hub-751.preview.emergentagent.com")
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ─── A. Per-country Field Coverage Heatmap ──────────────────────────────────

def test_audit_summary_has_au_ca_nz_coverage_blocks(admin_headers):
    """audit-summary must return three field_coverage_* blocks."""
    r = requests.get(f"{BASE_URL}/api/anz-intel/audit-summary", headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "field_coverage_au" in d
    assert "field_coverage_ca" in d
    assert "field_coverage_nz" in d
    assert len(d["field_coverage_au"]) >= 10   # 13 fields
    assert len(d["field_coverage_ca"]) >= 10   # 11 fields
    assert len(d["field_coverage_nz"]) >= 5    # 6 fields


def test_audit_summary_ca_field_coverage_shape(admin_headers):
    """CA coverage must have proper item shape + CA-specific fields."""
    r = requests.get(f"{BASE_URL}/api/anz-intel/audit-summary", headers=admin_headers, timeout=15)
    ca = r.json()["field_coverage_ca"]
    ca_field_keys = {x["field"] for x in ca}
    # CA-specific tracked fields
    assert "teer_category" in ca_field_keys
    assert "ee_eligibility" in ca_field_keys
    assert "pnp_eligibility" in ca_field_keys
    assert "quebec_eligibility" in ca_field_keys
    # Each item has the expected keys
    for item in ca:
        assert {"field", "label", "count_present", "count_missing", "pct_present", "source_hint"} <= set(item.keys())
        assert 0 <= item["pct_present"] <= 100


def test_audit_summary_nz_uses_nz_source_hints(admin_headers):
    """NZ shared-name fields should resolve to NZ-specific source URLs."""
    r = requests.get(f"{BASE_URL}/api/anz-intel/audit-summary", headers=admin_headers, timeout=15)
    nz = r.json()["field_coverage_nz"]
    # NZ tasks should reference careers.govt.nz not jobsandskills.gov.au
    tasks_item = next((x for x in nz if x["field"] == "tasks"), None)
    if tasks_item:
        assert "careers.govt.nz" in tasks_item["source_hint"] or "Stats NZ" in tasks_item["source_hint"]
    visa_item = next((x for x in nz if x["field"] == "visa_pathways"), None)
    if visa_item:
        assert "immigration.govt.nz" in visa_item["source_hint"]


def test_audit_rows_ca_returns_ca_tracked_fields(admin_headers):
    """audit-rows?country=CA must return CA tracked fields (not AU)."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/audit-rows?country=CA&limit=5",
        headers=admin_headers, timeout=15,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    tf_keys = {x["key"] for x in d["tracked_fields"]}
    # Must contain CA-specific fields, NOT AU-specific ones
    assert "teer_category" in tf_keys
    assert "ee_eligibility" in tf_keys
    assert "skillselect_tier" not in tf_keys  # AU-only
    assert "dama_eligibility" not in tf_keys  # AU-only
    # rows have country-aligned coverage keys
    if d["items"]:
        cov = d["items"][0]["coverage"]
        assert "teer_category" in cov


def test_audit_rows_nz_returns_nz_tracked_fields(admin_headers):
    """audit-rows?country=NZ must return NZ tracked fields."""
    r = requests.get(
        f"{BASE_URL}/api/anz-intel/audit-rows?country=NZ&limit=5",
        headers=admin_headers, timeout=15,
    )
    assert r.status_code == 200
    tf_keys = {x["key"] for x in r.json()["tracked_fields"]}
    assert "visa_pathways" in tf_keys
    assert "assessing_authority" in tf_keys
    # Should NOT include AU-only state nomination fields
    assert "state_territory_eligibility" not in tf_keys


# ─── B. IRCC Category Overrides ─────────────────────────────────────────────

def test_ircc_categories_get_returns_9_overridable(admin_headers):
    """GET /calc-rules/ircc-categories returns 9 overridable categories with defaults."""
    r = requests.get(f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories", headers=admin_headers, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["total_categories"] == 9
    cat_ids = {c["id"] for c in d["categories"]}
    expected = {
        "healthcare", "stem", "trade", "education", "transport",
        "physicians_ca_exp", "senior_managers_ca_exp", "researchers_ca_exp", "military_recruits",
    }
    assert expected == cat_ids
    # Sanity: healthcare must have default count >= 30
    hc = next(c for c in d["categories"] if c["id"] == "healthcare")
    assert hc["default_count"] >= 30
    assert hc["effective_count"] == hc["default_count"] - len(hc["removed_nocs"]) + len(set(hc["added_nocs"]) - set(hc["default_nocs"]))


def test_ircc_override_put_and_get_roundtrip(admin_headers):
    """PUT override → GET should reflect added+removed in effective_nocs."""
    # Use a non-existing test NOC code for added, and a known-default for removed
    cat_id = "trade"
    payload = {"added_nocs": ["88888"], "removed_nocs": ["72100"]}
    r = requests.put(
        f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/{cat_id}",
        headers=admin_headers, json=payload, timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    # Verify via GET
    g = requests.get(f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories", headers=admin_headers, timeout=15)
    trade = next(c for c in g.json()["categories"] if c["id"] == cat_id)
    assert trade["has_override"] is True
    assert "88888" in trade["effective_nocs"]
    assert "72100" not in trade["effective_nocs"]
    assert trade["added_nocs"] == ["88888"]
    assert trade["removed_nocs"] == ["72100"]

    # Cleanup
    requests.delete(f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/{cat_id}", headers=admin_headers, timeout=15)


def test_ircc_override_validation_rejects_bad_inputs(admin_headers):
    """Invalid NOC codes, overlap, and unknown categories must 400."""
    # Bad code format
    r1 = requests.put(
        f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/stem",
        headers=admin_headers,
        json={"added_nocs": ["abc"], "removed_nocs": []},
        timeout=15,
    )
    assert r1.status_code == 400

    # Overlap
    r2 = requests.put(
        f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/stem",
        headers=admin_headers,
        json={"added_nocs": ["21300"], "removed_nocs": ["21300"]},
        timeout=15,
    )
    assert r2.status_code == 400

    # Unknown category (french_language is NOT overridable)
    r3 = requests.put(
        f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/french_language",
        headers=admin_headers,
        json={"added_nocs": [], "removed_nocs": []},
        timeout=15,
    )
    assert r3.status_code == 400


def test_ircc_override_delete_reverts_to_defaults(admin_headers):
    """DELETE override → effective_count == default_count, has_override=False."""
    cat_id = "education"
    requests.put(
        f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/{cat_id}",
        headers=admin_headers, json={"added_nocs": ["77777"], "removed_nocs": []}, timeout=15,
    )
    r = requests.delete(
        f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/{cat_id}",
        headers=admin_headers, timeout=15,
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    g = requests.get(f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories", headers=admin_headers, timeout=15)
    edu = next(c for c in g.json()["categories"] if c["id"] == cat_id)
    assert edu["has_override"] is False
    assert edu["effective_count"] == edu["default_count"]


def test_ircc_reapply_dry_run_reports_overrides_used(admin_headers):
    """When an override exists, reapply must report overrides_applied_categories >= 1."""
    cat_id = "stem"
    requests.put(
        f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/{cat_id}",
        headers=admin_headers,
        json={"added_nocs": ["99999"], "removed_nocs": []},
        timeout=15,
    )
    try:
        r = requests.post(
            f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/reapply?dry_run=true",
            headers=admin_headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["dry_run"] is True
        assert d["overrides_applied_categories"] >= 1
        assert d["total_ca_codes_processed"] >= 100
    finally:
        requests.delete(f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/{cat_id}", headers=admin_headers, timeout=15)


def test_ircc_reapply_no_overrides_zero_count(admin_headers):
    """Without overrides, overrides_applied_categories must be 0."""
    # Cleanup all overrides first
    g = requests.get(f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories", headers=admin_headers, timeout=15)
    for c in g.json()["categories"]:
        if c["has_override"]:
            requests.delete(
                f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/{c['id']}",
                headers=admin_headers, timeout=15,
            )
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/calc-rules/ircc-categories/reapply?dry_run=true",
        headers=admin_headers, timeout=30,
    )
    assert r.status_code == 200
    assert r.json()["overrides_applied_categories"] == 0
