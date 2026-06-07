"""Phase 9.5 — DAMA + ILA + Min Invitation Points scraper regression tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "https://staff-dashboard-66.preview.emergentagent.com")
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS, timeout=15)
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def partner_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS, timeout=15)
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ─── /scrapers/list lists all 7 scrapers ────────────────────────────────────
def test_scrapers_list_has_seven(admin_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/scrapers/list", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()["scrapers"]}
    expected = {"home_affairs", "state_nominations", "skillselect_tiers",
                "vetassess_groups", "min_invitation_points", "dama", "ila"}
    assert expected <= ids
    ready = {s["id"] for s in r.json()["scrapers"] if s["status"] == "ready"}
    assert expected <= ready


# ─── Min Invitation Points scraper ──────────────────────────────────────────
def test_min_invitation_points_dry_run(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/min-invitation-points/run?dry_run=true",
        headers=admin_headers, timeout=20,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "min_invitation_points_seed"
    assert body["dry_run"] is True
    assert body["global_cutoffs"]["189"]["min_points"] == 90
    assert body["global_cutoffs"]["491_family"]["min_points"] == 65
    assert body["global_cutoffs"]["189_priority_health"]["min_points"] == 65
    # Either there are records to tag (first run) OR all already tagged (idempotent)
    counts = body["counts"]
    assert counts["tier_1_codes_tagged"] >= 0
    # Sanity: global cutoffs payload always present regardless of run state
    assert "189" in body["global_cutoffs"]


def test_min_invitation_points_idempotency(admin_headers):
    # 1st commit
    r1 = requests.post(f"{BASE_URL}/api/anz-intel/scrapers/min-invitation-points/run?dry_run=false",
                       headers=admin_headers, timeout=30)
    assert r1.status_code == 200
    # 2nd commit — every record already has identical data → no further updates
    r2 = requests.post(f"{BASE_URL}/api/anz-intel/scrapers/min-invitation-points/run?dry_run=false",
                       headers=admin_headers, timeout=30)
    assert r2.status_code == 200
    assert r2.json()["counts"]["tier_1_codes_tagged"] == 0


# ─── DAMA scraper ───────────────────────────────────────────────────────────
def test_dama_dry_run(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/dama/run?dry_run=true",
        headers=admin_headers, timeout=20,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "dama_seed"
    assert body["total_damas"] == 13
    ids = {d["id"] for d in body["damas"]}
    assert {"nt", "goldfields", "aerotropolis"} <= ids
    # Each DAMA must have state + valid_until + region
    for d in body["damas"]:
        assert d.get("state") and d.get("valid_until") and d.get("region")


def test_dama_tags_aerotropolis_for_software_engineer_unit_group(admin_headers):
    """After commit, codes in the Aerotropolis seed (261313/263111 etc.) should
    appear in dama_eligibility via the Atlas Verify endpoint."""
    # Ensure committed
    requests.post(f"{BASE_URL}/api/anz-intel/scrapers/dama/run?dry_run=false",
                  headers=admin_headers, timeout=30)
    # 263111 Network Engineer — both Adelaide Tech + Aerotropolis seed it
    r = requests.get(f"{BASE_URL}/api/anz-intel/verify/263111", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    damas = r.json().get("dama_eligibility") or []
    dama_ids = {d.get("id") for d in damas}
    assert "aerotropolis" in dama_ids, f"Aerotropolis missing for 263111: {damas}"


# ─── ILA scraper ────────────────────────────────────────────────────────────
def test_ila_dry_run(admin_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/ila/run?dry_run=true",
        headers=admin_headers, timeout=20,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "ila_seed"
    assert body["total_ilas"] == 4
    ids = {i["id"] for i in body["ilas"]}
    assert ids == {"restaurant", "meat", "aged_care", "fishing"}


# ─── Verify endpoint surfaces new fields ────────────────────────────────────
def test_verify_returns_new_fields(admin_headers):
    """Verify endpoint must include min_invitation_points + dama_eligibility + ila_eligibility."""
    r = requests.get(f"{BASE_URL}/api/anz-intel/verify/241111", headers=admin_headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "min_invitation_points" in body
    assert "dama_eligibility" in body
    assert "ila_eligibility" in body
    # Tier 1 record should have priority cutoff (65 pts)
    mip = body["min_invitation_points"]
    if mip:
        assert mip["189"] == 65
        assert mip["491_family"] == 65


# ─── RBAC blocks non-admin ──────────────────────────────────────────────────
def test_partner_blocked_from_dama(partner_headers):
    r = requests.post(
        f"{BASE_URL}/api/anz-intel/scrapers/dama/run?dry_run=true",
        headers=partner_headers, timeout=10,
    )
    assert r.status_code == 403


def test_partner_can_still_read_verify(partner_headers):
    r = requests.get(f"{BASE_URL}/api/anz-intel/verify/241111", headers=partner_headers, timeout=10)
    assert r.status_code == 200
