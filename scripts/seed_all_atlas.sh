#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# LEAMSS — One-command Atlas + Knowledge Base bootstrap
#
# WHY: MongoDB data does NOT travel with GitHub. After moving the repo to a new
# server, the DB is empty. This script repopulates occupation_master (Migration
# Atlas), the Knowledge Base, and marks records verified — by calling the same
# admin scraper endpoints the app uses internally. All endpoints are idempotent.
#
# USAGE:
#   chmod +x scripts/seed_all_atlas.sh
#   BASE_URL=http://localhost:8001 ADMIN_EMAIL=admin@leamss.com ADMIN_PASS=Admin@123 \
#     ./scripts/seed_all_atlas.sh
#
# Defaults: BASE_URL=http://localhost:8001, admin@leamss.com / Admin@123
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8001}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@leamss.com}"
ADMIN_PASS="${ADMIN_PASS:-Admin@123}"

echo "▶ Base URL: $BASE_URL"
echo "▶ Logging in as $ADMIN_EMAIL ..."

TOKEN=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASS\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin).get('token',''))")

if [ -z "$TOKEN" ]; then
  echo "✗ Login failed. Check BASE_URL / credentials / backend is running."
  exit 1
fi
echo "✓ Logged in."

AUTH=(-H "Authorization: Bearer $TOKEN")

run() {   # run <label> <endpoint-path>
  local label="$1"; local path="$2"
  echo "  • $label ..."
  curl -s -X POST "$BASE_URL$path?dry_run=false" "${AUTH[@]}" \
    | python3 -c "import sys,json;d=json.load(sys.stdin);print('    →', {k:d[k] for k in d if k in ('created','updated','inserted','skipped_unchanged','tagged','count','status','verified_now','already_verified')} or d)" \
    || echo "    ! failed (see server logs)"
}

echo ""
echo "═══ 1) AUSTRALIA scrapers ═══"
run "Home Affairs (ANZSCO base + visa eligibility, LIVE fetch)" "/api/anz-intel/scrapers/home-affairs/run"
run "State/Territory nominations"                                "/api/anz-intel/scrapers/state-nominations/run"
run "SkillSelect tiers"                                          "/api/anz-intel/scrapers/skillselect-tiers/run"
run "VETASSESS groups"                                           "/api/anz-intel/scrapers/vetassess-groups/run"
run "Min invitation points"                                     "/api/anz-intel/scrapers/min-invitation-points/run"
run "DAMA agreements"                                            "/api/anz-intel/scrapers/dama/run"
run "ILA agreements"                                             "/api/anz-intel/scrapers/ila/run"

echo ""
echo "═══ 2) CANADA scrapers ═══"
run "NOC Canada base (from CSV in repo)"     "/api/anz-intel/scrapers/noc-canada/run"
run "IRCC Express Entry streams"             "/api/anz-intel/scrapers/ircc-ee-streams/run"
run "11 PNPs"                                "/api/anz-intel/scrapers/pnp-canada/run"
run "IRCC round cutoffs"                     "/api/anz-intel/scrapers/ircc-round-cutoffs/run"
run "AIP/RCIP/FCIP regional pilots"          "/api/anz-intel/scrapers/ca-regional-pilots/run"
run "Quebec PSTQ"                            "/api/anz-intel/scrapers/quebec-immigration/run"

echo ""
echo "═══ 3) NEW ZEALAND scrapers ═══"
run "NZ ANZSCO base seed"        "/api/anz-intel/scrapers/nz-anzsco-seed/run"
run "NZ Green List (Tier 1/2)"   "/api/anz-intel/scrapers/nz-green-list/run"
run "NZ AEWV + SMC"              "/api/anz-intel/scrapers/nz-aewv-smc/run"
run "NZ sector agreements"       "/api/anz-intel/scrapers/nz-sector-agreements/run"

echo ""
echo "═══ 4) AUTO-VERIFY (so records show on public Atlas) ═══"
for C in AU CA NZ; do
  echo "  • Auto-verify $C ..."
  curl -s -X POST "$BASE_URL/api/anz-intel/auto-verify/$C/run?dry_run=false&min_coverage_pct=70" "${AUTH[@]}" \
    | python3 -c "import sys,json;d=json.load(sys.stdin);print('    →', {k:d[k] for k in d if k in ('verified_now','already_verified','skipped','status')} or d)" \
    || echo "    ! failed"
done

echo ""
echo "═══ 5) KNOWLEDGE BASE seed (countries/visas/skill-bodies) ═══"
curl -s -X POST "$BASE_URL/api/eligibility/kb/seed/run" "${AUTH[@]}" \
  | python3 -c "import sys,json;print('    →', json.load(sys.stdin))" || echo "    ! failed"

echo ""
echo "✅ Done. Check Admin → Migration Atlas + Knowledge Base. Re-run anytime (idempotent)."
echo "ℹ  NOTE: ABS Excel enrichment (Occupation Profile / Labour Market SA4 / Industry /"
echo "   Employment Projection) is NOT in this repo — re-upload those via"
echo "   Admin → Occupation Master Import (/api/occupation-master-import)."
