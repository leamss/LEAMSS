"""Phase 6.9.2 / 6.9.3 / 6.9.4 / 6.9.5 — Full backend suite.

Validates:
  • Bulk import preview + commit (CSV)
  • AI Draft + Polish endpoints (mocked OR real)
  • Settings + auto-flag outdated
  • Country Templates CRUD + verify
"""
import io
import os
import uuid
import pytest
import requests

API = os.environ.get("REACT_APP_BACKEND_URL") or "https://staff-dashboard-66.preview.emergentagent.com"
BASE = f"{API}/api"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"}, timeout=10)
    return r.json()["token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ════════════════════════════════════════════════════════════════
# 6.9.2 — Bulk Import
# ════════════════════════════════════════════════════════════════
def _csv_bytes(rows):
    """Build a small CSV blob from a list of dicts (first dict's keys → header)."""
    if not rows:
        return b""
    keys = list(rows[0].keys())
    lines = [",".join(keys)]
    for r in rows:
        lines.append(",".join(str(r.get(k, "")).replace(",", " ") for k in keys))
    return ("\n".join(lines) + "\n").encode("utf-8")


def test_import_preview_detects_columns(admin_headers):
    """Preview must auto-detect 'code' and 'title' columns and parse first 10 rows."""
    csv = _csv_bytes([
        {"anzsco_code": "999991", "occupation_title": "Test Pilot A", "skill_level": "1", "unit_group_name": "Aerospace"},
        {"anzsco_code": "999992", "occupation_title": "Test Pilot B", "skill_level": "2", "unit_group_name": "Aerospace"},
    ])
    files = {"file": ("anzsco_sample.csv", csv, "text/csv")}
    data = {"country_code": "AU", "classification_type": "ANZSCO"}
    r = requests.post(f"{BASE}/occupation-master/import/preview", files=files, data=data, headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True
    assert d["total_rows"] == 2
    assert d["detected_mapping"]["code"] == "anzsco_code"
    assert d["detected_mapping"]["title"] == "occupation_title"
    assert len(d["sample_rows"]) == 2


def test_import_commit_inserts_and_skips_duplicates(admin_headers):
    """Commit must insert new codes as 'draft' and skip duplicates."""
    test_code = f"99{uuid.uuid4().hex[:4].upper()}"
    csv = _csv_bytes([
        {"code": test_code, "title": f"E2E Import {test_code}", "skill_level": "1"},
        {"code": "261313", "title": "Software Engineer", "skill_level": "1"},  # already in DB
    ])
    files = {"file": ("import.csv", csv, "text/csv")}
    data = {
        "country_code": "AU", "classification_type": "ANZSCO",
        "classification_version": "TEST v1", "on_duplicate": "skip",
    }
    r = requests.post(f"{BASE}/occupation-master/import/commit", files=files, data=data, headers=admin_headers, timeout=10)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["imported"] == 1
    assert d["skipped"] == 1  # 261313 already exists
    # Verify our inserted record is draft + correct version
    g = requests.get(f"{BASE}/occupation-master?country=AU&search={test_code}", headers=admin_headers, timeout=10)
    found = [i for i in g.json()["items"] if i["code"] == test_code]
    assert len(found) == 1
    assert found[0]["status"] == "draft"
    assert found[0]["classification_version"] == "TEST v1"
    # Cleanup
    requests.delete(f"{BASE}/occupation-master/{found[0]['occupation_id']}", headers=admin_headers)


def test_import_commit_update_mode(admin_headers):
    """on_duplicate=update should refresh existing records but preserve verification."""
    csv = _csv_bytes([
        {"code": "261313", "title": "Software Engineer (REFRESHED TEST)", "skill_level": "1"},
    ])
    files = {"file": ("upd.csv", csv, "text/csv")}
    data = {
        "country_code": "AU", "classification_type": "ANZSCO",
        "classification_version": "REFRESH TEST", "on_duplicate": "update",
    }
    r = requests.post(f"{BASE}/occupation-master/import/commit", files=files, data=data, headers=admin_headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["updated"] == 1
    # Title should change
    g = requests.get(f"{BASE}/occupation-master?country=AU&search=261313", headers=admin_headers, timeout=10)
    found = [i for i in g.json()["items"] if i["code"] == "261313"][0]
    assert "REFRESHED TEST" in found["title"]
    # Reset for downstream tests
    requests.put(f"{BASE}/occupation-master/{found['occupation_id']}",
                 json={"title": "Software Engineer", "classification_version": "Legacy migration · 2026-05-22"},
                 headers=admin_headers, timeout=10)


def test_import_rejects_non_admin(admin_headers):
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    p_headers = {"Authorization": f"Bearer {p.json()['token']}"}
    csv = _csv_bytes([{"code": "X1", "title": "X"}])
    r = requests.post(f"{BASE}/occupation-master/import/preview",
                      files={"file": ("x.csv", csv, "text/csv")},
                      data={"country_code": "AU", "classification_type": "ANZSCO"},
                      headers=p_headers, timeout=10)
    assert r.status_code == 403


def test_import_missing_required_columns(admin_headers):
    csv = _csv_bytes([{"random_col": "x"}])
    r = requests.post(f"{BASE}/occupation-master/import/preview",
                      files={"file": ("bad.csv", csv, "text/csv")},
                      data={"country_code": "AU", "classification_type": "ANZSCO"},
                      headers=admin_headers, timeout=10)
    d = r.json()
    assert d["ok"] is False
    assert "code" in d["error"].lower() or "title" in d["error"].lower()


# ════════════════════════════════════════════════════════════════
# 6.9.3 — AI Draft & Polish (light tests — real Claude call)
# ════════════════════════════════════════════════════════════════
def test_polish_text_returns_polished(admin_headers):
    """Polish endpoint must return string of similar length without changing key facts."""
    r = requests.post(
        f"{BASE}/kb/polish-text",
        json={"text": "the software engineer designs software. they writes code.", "field_label": "Description"},
        headers=admin_headers, timeout=60,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True
    assert "software" in d["polished"].lower()
    assert d["polished"] != d["original"]  # something changed


def test_polish_text_rejects_empty(admin_headers):
    r = requests.post(f"{BASE}/kb/polish-text", json={"text": ""}, headers=admin_headers, timeout=10)
    assert r.status_code == 400


def test_generate_ai_draft_caches_result(admin_headers):
    """Generate AI draft on AU 261313 — result should land in ai_draft block."""
    g = requests.get(f"{BASE}/occupation-master?country=AU&search=261313", headers=admin_headers, timeout=10)
    items = [i for i in g.json()["items"] if i["code"] == "261313"]
    occ_id = items[0]["occupation_id"]
    r = requests.post(f"{BASE}/occupation-master/{occ_id}/ai-draft", headers=admin_headers, timeout=90)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True
    assert d["ai_draft"]["generated_at"] is not None
    assert d["ai_draft"]["generated_by_model"] == "claude-sonnet-4-6"
    # Description should be non-empty
    assert len(d["ai_draft"]["description"]) > 30
    # Typical tasks should be a list of strings
    assert isinstance(d["ai_draft"]["typical_tasks"], list)


def test_ai_draft_rejects_non_admin(admin_headers):
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    p_headers = {"Authorization": f"Bearer {p.json()['token']}"}
    # Pick any occ id
    g = requests.get(f"{BASE}/occupation-master?limit=1", headers=admin_headers, timeout=10)
    occ_id = g.json()["items"][0]["occupation_id"]
    r = requests.post(f"{BASE}/occupation-master/{occ_id}/ai-draft", headers=p_headers, timeout=10)
    assert r.status_code == 403


# ════════════════════════════════════════════════════════════════
# 6.9.4 — Settings + Auto-flag
# ════════════════════════════════════════════════════════════════
def test_settings_default_creation(admin_headers):
    r = requests.get(f"{BASE}/kb/settings", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["outdated_threshold_months"] >= 1
    assert d["verification_gate_percent"] >= 50
    assert isinstance(d["enforce_verified_only"], bool)


def test_settings_update_works(admin_headers):
    r = requests.put(f"{BASE}/kb/settings", json={"outdated_threshold_months": 4, "verification_gate_percent": 85}, headers=admin_headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["outdated_threshold_months"] == 4
    assert r.json()["verification_gate_percent"] == 85
    # Reset
    requests.put(f"{BASE}/kb/settings", json={"outdated_threshold_months": 6, "verification_gate_percent": 90}, headers=admin_headers)


def test_auto_flag_outdated_runs_clean(admin_headers):
    """No verified records yet → no flips, but endpoint must still return OK."""
    r = requests.post(f"{BASE}/kb/auto-flag-outdated", headers=admin_headers, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["occupations_flagged_outdated"] == 0  # nothing verified yet
    assert "cutoff_date" in d


# ════════════════════════════════════════════════════════════════
# 6.9.5 — Country Templates
# ════════════════════════════════════════════════════════════════
def test_templates_list_has_three_countries(admin_headers):
    r = requests.get(f"{BASE}/country-templates", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["count"] >= 3
    ccs = {t["country_code"] for t in d["items"]}
    assert {"AU", "CA", "NZ"}.issubset(ccs)


def test_templates_get_au_has_factors(admin_headers):
    r = requests.get(f"{BASE}/country-templates/AU", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert d["country_code"] == "AU"
    assert d["country_name"] == "Australia"
    assert d["status"] == "draft"
    assert len(d["factors"]) > 0
    # Each factor must have factor_id + options
    for f in d["factors"]:
        assert f.get("factor_id")
        assert "options" in f


def test_templates_update_factor_reverts_to_draft(admin_headers):
    """Editing factors must auto-set status=draft so admin re-verifies."""
    # Get current
    r = requests.get(f"{BASE}/country-templates/NZ", headers=admin_headers, timeout=10)
    nz = r.json()
    new_pass_mark = nz["pass_mark"] + 1
    upd = requests.put(f"{BASE}/country-templates/NZ", json={"pass_mark": new_pass_mark}, headers=admin_headers, timeout=10)
    assert upd.status_code == 200
    assert upd.json()["pass_mark"] == new_pass_mark
    assert upd.json()["status"] == "draft"
    # Reset
    requests.put(f"{BASE}/country-templates/NZ", json={"pass_mark": nz["pass_mark"]}, headers=admin_headers)


def test_templates_verify_endpoint(admin_headers):
    # Create a test template to avoid touching AU/CA/NZ
    test_cc = "ZZ"  # placeholder country
    # Cleanup first
    requests.delete(f"{BASE}/country-templates/{test_cc}", headers=admin_headers)
    create = requests.post(f"{BASE}/country-templates", json={
        "country_code": test_cc, "country_name": "Test Country",
        "factors": [{"factor_name": "Age", "factor_type": "select", "options": [{"label": "25-32", "points": 30}]}],
        "pass_mark": 60, "visa_subclasses": [],
    }, headers=admin_headers, timeout=10)
    assert create.status_code == 200
    # Verify
    v = requests.post(f"{BASE}/country-templates/{test_cc}/verify",
                      json={"source_reference": "https://test.gov/", "review_notes": "Test"},
                      headers=admin_headers, timeout=10)
    assert v.status_code == 200
    assert v.json()["status"] == "verified"
    assert v.json()["verification"]["source_reference"] == "https://test.gov/"
    # Cleanup — verified can't be hard deleted via DELETE, so just leave it (or force-delete via DB)
    # We've already validated; cleanup will happen via PUT to draft status then DELETE
    requests.put(f"{BASE}/country-templates/{test_cc}", json={"status": "draft"}, headers=admin_headers)
    requests.delete(f"{BASE}/country-templates/{test_cc}", headers=admin_headers)


def test_templates_partner_can_read_not_modify(admin_headers):
    p = requests.post(f"{BASE}/auth/login", json={"email": "partner@leamss.com", "password": "Partner@123"}, timeout=10)
    if p.status_code != 200:
        pytest.skip("partner not seeded")
    p_headers = {"Authorization": f"Bearer {p.json()['token']}"}
    # Can list
    r = requests.get(f"{BASE}/country-templates", headers=p_headers, timeout=10)
    assert r.status_code == 200
    # Cannot create
    c = requests.post(f"{BASE}/country-templates", json={"country_code": "XX", "country_name": "Hack"}, headers=p_headers, timeout=10)
    assert c.status_code == 403
    # Cannot update
    u = requests.put(f"{BASE}/country-templates/AU", json={"pass_mark": 50}, headers=p_headers, timeout=10)
    assert u.status_code == 403


# ════════════════════════════════════════════════════════════════
# Regression — sales endpoints still work
# ════════════════════════════════════════════════════════════════
def test_sales_search_still_returns_88(admin_headers):
    r = requests.get(f"{BASE}/sales/occupations/search?q=&limit=200", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    assert r.json()["count"] == 88


def test_calculator_still_works(admin_headers):
    """Calculator endpoint must continue using legacy rules engine (templates only edited via UI yet)."""
    r = requests.post(f"{BASE}/sales/calculator/calculate-batch",
                      json={
                          "profile": {
                              "marital_status": "single",
                              "primary_applicant": {
                                  "personal": {"age": 30},
                                  "education": {"highest_qualification": "bachelor"},
                                  "language": {"scores": {"overall": 7.5, "listening": 7.5, "reading": 7, "writing": 7, "speaking": 7.5}},
                                  "professional": {"years_experience_total": 6, "current_profession": "SE"},
                                  "au_extras": {}, "ca_extras": {}, "nz_extras": {},
                              },
                          },
                          "targets": [{"country": "AU", "visa_subclass": "189"}],
                      },
                      headers=admin_headers, timeout=15)
    assert r.status_code == 200
    assert r.json()["results"][0]["total"] >= 60
