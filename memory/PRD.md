# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client. Expanding to a full multi-department Employee Portal with production-grade RBAC.

> **📌 Update (Feb 13, 2026):** `CHANGELOG.md` now tracks all completed phases (incl. **Phase 3A — Attendance & Leave** with full company policies). `ROADMAP.md` lists prioritized backlog. This PRD remains the static reference for original requirements.

### 🎯 Phase 13 — Public Atlas Pages (SEO + Lead Capture) (Jun 9, 2026)
**Status:** ✅ COMPLETE — 13/13 active pytest PASS (1 by-design skip) · testing_agent reports 100% backend + 100% frontend.

Sir's ask: "P2 Client-facing public Atlas pages (/atlas/au/261313) for SEO + organic lead capture".

**Backend** — `routers/public_atlas.py` (no auth):
- `GET /api/public-atlas/featured` — 12 hero cards across AU/CA/NZ + country totals
- `GET /api/public-atlas/{country}/list?limit=N&search=Q` — paginated verified browse
- `GET /api/public-atlas/{country}/{code}` — single occupation deep-dive with `seo` block (page_title, meta_description, og_image, canonical_url, JSON-LD `@type=Occupation`) + similar codes + cross_country
- `GET /api/public-atlas/sitemap.xml` — auto-generated sitemap of all 720+ verified URLs
- `POST /api/public-atlas/lead` — captures lead → `leads` collection with `source=public_atlas` + tags. Honeypot field `company_url` silently drops bots. Rate-limited 15/min per IP (in-memory). Pydantic email validation.
- Filters: only `status="verified"` records exposed publicly. Admin metadata (verification, ai_draft) stripped from response.
- Absolute URLs (https://) for canonical_url + og_image — reads `FRONTEND_URL` env.

**Frontend** — `pages/PublicAtlas.jsx` (no `<ProtectedRoute>`):
- `/atlas` — Hero + 3 country cards + 12-tile featured grid
- `/atlas/:country` — Browseable list with live search
- `/atlas/:country/:code` — Single occupation page with sticky `LeadCaptureForm` on the right rail
- `applySEO()` injects `<title>`, meta description, og:image, og:title, canonical, JSON-LD into `<head>` per page
- Lead form has hidden honeypot field absolutely positioned off-screen
- Routes registered in `App.js` lines 92-94 (before login redirect)

**Tests `test_phase13_public_atlas.py` (13/13 active + 1 skipped):**
1. Featured works without auth
2. Single occupation no-auth + SEO + JSON-LD
3-5. Unknown country (404), unknown code (404), invalid format (400)
6. Draft codes never exposed
7. Country list search filter
8. Country list returns meta + seo
9. Sitemap XML valid + 50+ URLs
10-13. Lead capture (success, honeypot, invalid email, stored in DB)
14. Rate limit (skipped by default — RUN_RATELIMIT_TEST=1 to enable)

**Post-test fixes applied:**
- Cleaned page title (removed "Legacy migration · 2026-05-22" fragment from classification_version)
- Absolute URLs for canonical_url + og_image (now uses FRONTEND_URL env)
- Replaced AU "Chef 351311" (draft) with AU "263111 Network Engineer" in featured → all 12 cards render
- Rate-limit threshold bumped 5→15/min to reduce false positives in shared-IP environments


### 🎯 Phase 12 — NZ Atlas Full Build + Bulk Auto-Verify Tool (Jun 9, 2026)
**Status:** ✅ COMPLETE — 16/16 new pytest PASS · 49 total tests PASS · testing_agent_v3_fork reports 100%/100% backend+frontend.

Sir's ask: "P1 New Zealand Atlas Full Build (Green List Tier 1/2 scrapers, LTSSL/RSSL) + P2 Bulk Auto-Verify Tool for Occupation Codes".

**A) NZ Atlas — 4 New Scrapers:**
- `core/scrapers/nz_anzsco_seed.py` — 243 ANZSCO 1.3 base records inserted idempotently (Managers, Professionals, Engineers, ICT, Health, Education, Trades, Care Workers, Plant Operators).
- `core/scrapers/nz_green_list.py` — Classifies 91 Tier 1 (Straight to Residence) + 23 Tier 2 (Work to Residence 24mo) occupations. Notes LTSSL/RSSL retired 2022 → replaced by Green List Tier 2 + AEWV.
- `core/scrapers/nz_aewv_smc.py` — AEWV eligibility (skill_level 1-3 eligible) + SMC 6-point base (skill_points 2-6 + green_list_auto_pass flag).
- `core/scrapers/nz_sector_agreements.py` — 6 sectors: CISA (31 codes), Care Workforce (13), Transport (9), Tourism (7), Meat (1), Snow/Adventure (2).
- 4 new endpoints under `/api/anz-intel/scrapers/nz-*/run`.
- `TRACKED_FIELDS_NZ` expanded from 6 → 9 fields including `nz_green_list_tier`, `aewv_eligibility`, `smc_points_breakdown`, `sector_agreement_eligibility`.
- NZ heatmap shows 100% coverage on 7 of 9 fields after running all 4 scrapers.

**B) Bulk Auto-Verify Tool:**
- `core/auto_verify.py` — per-country verification rules:
  - **AU**: assessing_authority + visa_pathways + skillselect_tier + min_invitation_points
  - **CA**: teer_category + ee_eligibility + hierarchy + (pnp OR quebec OR regional_pilot)
  - **NZ**: skill_level + assessing_authority + visa_pathways + (green_list_tier OR aewv_eligibility)
- 3 new admin endpoints: `GET /auto-verify/rules`, `GET /auto-verify/{country}/preview`, `POST /auto-verify/{country}/run`.
- `min_coverage_pct` filter (default 70%) — records below threshold are skipped.
- Idempotent: re-runs return `verified_now=0`, `already_verified=N`.
- Records flipped from `status="draft"` → `status="verified"` with audit footprint (auto_verified_at, auto_verified_by, auto_verify_version, auto_verify_pct).
- New frontend tab in `AnzIntelAudit.jsx` — `AutoVerifyTab` component with rules card + min coverage input + preview table + run button. Uses `key={country}` for clean remount.

**Live state after Phase 12:**
- NZ Atlas: 243 records (was 20) — all auto-verified
- CA Atlas: 516 records — 103 auto-verifiable
- AU Atlas: 932 records — 370 auto-verifiable, 558 below threshold

**Tests `test_phase12_nz_atlas_and_autoverify.py` (16/16 PASS):**
1-2. Scrapers list contains 4 new NZ entries
3-6. Each NZ scraper returns correct counts (Tier 1/2, AEWV, SMC, Sector distribution)
7. Audit summary now has 200+ NZ records
8. NZ tracked fields include Phase 12 additions
9. Software Engineer (261313) spot-check = Green List Tier 1
10. Partner blocked on NZ scrapers
11-16. Auto-Verify rules + preview + dry-run + idempotency + 400 on unsupported + partner-blocked


### 🎯 Phase 11 — Per-country Heatmap (CA + NZ) + IRCC Category Overrides (Jun 9, 2026)
**Status:** ✅ COMPLETE — 11/11 new pytest PASS · 22/22 regression PASS · UI live for both features.

Sir's ask: "Per-country Field Coverage Heatmap (CA + NZ — currently AU-only) + Calculator Rules Editor — admin override UI for IRCC category NOC lists".

**A) Heatmap CA + NZ (Backend):**
- `routers/anz_intel.py`:
  - `_humanize()` + `_source_hint(field, country)` extended with CA/NZ field labels & NZ-specific source URLs (careers.govt.nz, immigration.govt.nz, NZQA).
  - `/audit-summary` now also returns `field_coverage_ca` (11 fields) and `field_coverage_nz` (6 fields) alongside existing AU block.
  - `/audit-rows?country=CA|NZ` uses `_tracked_fields_for(country)` so each country sees its own fields.

**A) Heatmap (Frontend `AnzIntelAudit.jsx`):**
- Removed placeholder `CoverageCAorNZ`. Real heatmap now renders for CA + NZ.
- `CoverageTab` and `HeatmapTab` accept `country` prop and switch the right field list/data.
- Per-Occupation Heatmap tab is now visible for ALL countries (was AU-only).

**B) IRCC Category Overrides (Backend):**
- `routers/anz_intel.py` — 4 new admin endpoints under `/calc-rules/ircc-categories`:
  - `GET` → returns 9 overridable categories with default_nocs, added_nocs, removed_nocs, effective_nocs (merged).
  - `PUT /{category_id}` → save added/removed NOC arrays with strict 5-digit validation, no-overlap rule.
  - `DELETE /{category_id}` → revert to hardcoded defaults.
  - `POST /reapply?dry_run=` → re-classify all 516 CA NOCs using current overrides.
- `core/scrapers/ircc_ee_streams.py` — `classify()` accepts optional `noc_sets_override`; new `_build_effective_noc_map(db)` merges defaults with `ircc_category_overrides` collection; `apply_to_db()` reports `overrides_applied_categories` count.
- New collection: `ircc_category_overrides` (one doc per category with added_nocs/removed_nocs/updated_at/updated_by).

**B) IRCC Editor (Frontend `CalculatorRulesEditor.jsx`):**
- Added section toggle: **Scoring Tables (Phase 9.6)** ↔ **IRCC EE Category NOCs (Phase 11)**.
- New `IrccCategoriesEditor` + 9 `IrccCategoryCard` components — each card has chip-based add/remove inputs, defaults preview, save/reset buttons, and live effective_count badge.
- "Re-apply to 516 CA NOCs" button triggers a full re-classification with success summary.

**Tests `test_phase11_heatmap_and_ircc_overrides.py` (11/11 PASS):**
1. audit-summary has au/ca/nz coverage blocks
2. CA coverage has CA-specific fields & correct shape
3. NZ uses NZ-specific source hints (careers.govt.nz, immigration.govt.nz)
4. audit-rows CA returns CA tracked fields (not AU)
5. audit-rows NZ returns NZ tracked fields
6. GET ircc-categories returns 9 overridable
7. PUT + GET roundtrip reflects effective_nocs
8. Validation rejects bad NOC format, overlap, unknown category
9. DELETE reverts to defaults
10. Reapply dry-run reports overrides_applied_categories ≥ 1
11. Reapply with no overrides reports 0

**Files:**
- MOD `/app/backend/routers/anz_intel.py` — Phase 11 endpoints + per-country audit
- MOD `/app/backend/core/scrapers/ircc_ee_streams.py` — override-aware classification
- MOD `/app/frontend/src/pages/admin/AnzIntelAudit.jsx` — real CA/NZ heatmap
- MOD `/app/frontend/src/pages/admin/CalculatorRulesEditor.jsx` — IRCC section + 9 category cards
- NEW `/app/backend/tests/test_phase11_heatmap_and_ircc_overrides.py` — 11 tests


### 🏆 Phase 10.8 — Compare Programs Side-by-Side (Jun 8, 2026)
**Status:** ✅ COMPLETE — 7/7 pytest PASS · UI live with best-fit auto-highlight · Backend scoring algorithm.

Sir's ask: "Compare Programs Side-by-Side enhancement (depends on rich auto-suggest data, now ready to build)".

**Backend changes:**
- `routers/sales_occupations.py`:
  - `/sales/occupations/compare` max items bumped: 4 → **5**
  - Per-item enrichment block: appends full Phase 10 atlas data from `occupation_master`:
    - `teer_category`, `teer_label`, `ee_eligibility`, `pnp_eligibility`,
    - `ircc_round_cutoffs`, `regional_pilot_eligibility`, `quebec_eligibility`,
    - `skillselect_tier`, `assessing_authority`, `state_nomination`,
    - `min_invitation_points`, `dama_eligibility`, `ila_eligibility`, `classification_version`
  - NEW `_compute_best_fit_score(item)` — transparent scoring rubric (country-agnostic):
    - In-demand → +20
    - Low min-points → +(100 − mp/2) cap +50
    - Higher age limit → +(age − 30) cap +15
    - Atlas TEER label → +5
    - Each federal program (FSWP/CEC/FSTP) → +10
    - PNPs/States count → +(count × 3) cap +30
    - SkillSelect Tier 1 → +15 (AU)
    - Round cutoffs present → +5
    - Regional pilots + DAMA + ILA → +(count × 2) cap +15
    - Quebec eligible → +10 (+5 extra if priority section)
  - Endpoint marks exactly ONE item with `best_fit=true` (the highest scorer)

**Frontend (rebuilt):** `/app/frontend/src/pages/sales/OccupationCompare.jsx` (~430 lines):
- Top banner: **"🏆 Best Fit (Score X) · Country · Code · Title"** with green emerald glow
- Card grid (auto 2/3/4/5 columns) — best-fit card gets:
  - Thick emerald top-border
  - Floating "🏆 Best Fit" ribbon
  - Drop shadow with emerald tint
- Per-card quick stats: PNPs · Cats · Pilots · QC ✓ (CA) or Visas · States · Tier (AU)
- **Detailed Comparison Table** with row-bands:
  - Title · Classification · Skill/TEER · In Demand
  - **🇨🇦 IRCC Federal Programs:** FSWP/CEC/FSTP (✓/✗) · Categories (chips with icons) · PNPs (badges) · Regional Pilots (counts by type) · Quebec PSTQ (with ⭐ priority) · Latest CRS Cutoff
  - **🇦🇺 Australia Specifics:** Skill Body · SkillSelect Tier · State Nominations · Min Invit Pts · DAMA+ILA
  - **📊 Cost/Process:** Min Points · Age Limit · Body Fee · Processing Weeks
  - **🏆 Best-Fit Score** row with 🏆 indicator
- Best-fit column highlighted with subtle green background
- Sections only render if at least one item has data for that country

**AtlasAutoSuggestModal.jsx integration:**
- NEW "Compare All" button shown when AI returns 2+ suggestions
- Click → stores `compare_ids` in sessionStorage, opens `/sales/occupations/compare` in new tab
- Sales workflow: AI suggests 5 NOCs → "Compare All" → instant side-by-side

**Live Verification (3-CA comparison):**
- 21231 SW Engineer: Score **157** (FSWP+CEC, 7 PNPs, 3 pilots, 1 cat, QC ✓)
- 31102 Family Physician: Score **136** (FSWP+CEC, 2 PNPs, 0 pilots, 3 cats, QC ✓)
- 72310 Carpenter: Score **168** 🏆 (FSWP+CEC+**FSTP**, 6 PNPs, **14 pilots**, 2 cats, QC ✓) → **Best Fit**

**Tests (7/7 PASS):**
1. Compare returns atlas data per item
2. Exactly one item assigned best_fit=true
3. Carpenter (FSTP+pilots) beats SW Engineer in score
4. Pydantic min 2 / max 5 validation
5. AU-specific fields (skillselect_tier/state_nomination) surface for AU codes
6. Cross-country mix (AU + CA) renders both
7. Quebec bonus reflected in score

**Files:**
- MOD `/app/backend/routers/sales_occupations.py` — atlas enrichment + best-fit scoring + max 5 items
- REWRITTEN `/app/frontend/src/pages/sales/OccupationCompare.jsx` — rich side-by-side comparison
- MOD `/app/frontend/src/pages/sales/components/AtlasAutoSuggestModal.jsx` — "Compare All" button
- NEW `/app/backend/tests/test_phase108_compare_side_by_side.py` — 7 tests


### 🇨🇦🇫🇷 Phase 10.7 — Quebec PSTQ/PEQ + Multi-Country AI Auto-Suggest UI (Jun 8, 2026)
**Status:** ✅ COMPLETE — 13/13 new pytest PASS · Quebec live · AI Auto-Suggest now multi-country (AU/CA/NZ) · UI button in Sales Wizard.

Sir's ask: "Quebec PEQ/PSTQ separate system + AI Auto-Suggest UI configured for ALL countries (present + future)".

---

**Part A — Quebec PSTQ + PEQ-Legacy Seed**

Quebec is the ONLY Canadian province that runs its own immigration system separate from federal IRCC Express Entry and the 11 PNPs.

| Program | Status | Notes |
|---------|--------|-------|
| **PSTQ — Programme de sélection des travailleurs qualifiés** | ✅ Active (2024-11 →) | Current main skilled-worker stream |
| **PEQ — Programme de l'expérience québécoise** | ❌ Closed 2025 | Legacy reference only |
| **CAQ — Certificat d'acceptation du Québec** | Issued post-PSTQ | Step toward federal IRCC PR |

**4 PSTQ Sections seeded:**
| Section | Name | FEER Eligible | French | Notes |
|---------|------|---------------|--------|-------|
| **A** | Skilled Workers (priority TEER 0-2) | 0/1/2 | Oral 7+ Written 5+ | 21 priority NOCs |
| **B** | Skilled Workers (priority TEER 3-5) | 3/4/5 | Oral 5+ | 8 priority NOCs |
| **C** | Regulated Professions | 0-5 | Oral 7+ Written 5+ | Requires Quebec authority licence |
| **D** | Quebec-Graduated Applicants | 0-5 | Oral 7+ Written 5+ | For QC post-secondary grads |

**Live Verification (Atlas Verify):**
- 21231 SW Engineer (TEER 1) → A ⭐ + D
- 31102 Family Physician (TEER 1) → A + **C (regulated)** + D
- 72310 Carpenter (TEER 2) → A + D, NOT C (not regulated)
- 85100 Livestock Labourer (TEER 5) → **B only** (Section A excludes TEER 5)

**Section Distribution (live):** Section A = 307 NOCs · B = 209 · C = 52 (regulated) · D = 516 (all)

---

**Part B — AI Atlas Auto-Suggest: Multi-Country (Future-Proof)**

Previously CA-only; now accepts `country_code` for **AU/CA/NZ** (and any future country added to `occupation_master`).

**Backend changes:** `routers/sales_ai_helpers.py` → `/atlas-auto-suggest`:
- Accepts `country_code: "AU" | "CA" | "NZ"` (default CA for backward compat)
- Renamed `province_code` → `region_code` (works for province/state)
- Country-aware system prompt + classification label (NOC 2021 vs ANZSCO)
- Per-country atlas enrichment block:
  - **AU:** skillselect_tier, assessing_authority, state_nomination, visa_pathways, min_invitation_points
  - **CA:** teer_category, ee_eligibility, pnp_eligibility, ircc_round_cutoffs, regional_pilot_eligibility, quebec_eligibility (NEW)
  - **NZ:** assessing_authority, visa_pathways (extends in Phase 11)
- Region preference re-sorts PNPs/states with selected region first

**Frontend (NEW):** `pages/sales/components/AtlasAutoSuggestModal.jsx` (~300 lines):
- Free-text candidate description input (15-2000 chars)
- Country badge auto-detected from wizard
- Region selector (12 CA provinces incl. QC · 8 AU states · 6 NZ regions)
- Calls `/api/sales/ai/atlas-auto-suggest` with Haiku 4.5 routing
- Each result card shows:
  - NOC/ANZSCO code + confidence badge (HIGH/MEDIUM/LOW)
  - "Region match" badge if applicable
  - **CA cards:** TEER · Federal Programs · Categories (chips with icons) · PNPs (region highlighted gold) · CRS Cutoffs · Regional Pilots · Quebec PSTQ sections
  - **AU cards:** Skill Level · Skill Body · SkillSelect Tier · Visa Pathways · State Nominations
  - **NZ cards:** Skill Level · Visa Pathways count
- "Pick this" button → auto-fills `occupation_code` + `occupation_country` + auto-opens Atlas Verify Card

**Step3Profile.jsx changes:**
- New "AI Atlas Auto-Suggest" orange button next to existing "AI Occupation Helper"
- Modal opens with current country from wizard state
- On pick → updates wizard data + auto-opens Atlas Verify Card

**Live AI Calls (verified end-to-end):**

| Test | Result | Atlas data |
|------|--------|------------|
| 🇦🇺 "Civil engineer, 8yr infra → NSW" | 233211 Civil Engineer (HIGH) | Skill Lv 1 · Skill Body: EA |
| 🇨🇦 "Family physician, 8yr GP → QC" | 31102 (HIGH) | TEER 1 · Healthcare+Physicians-CA · **Quebec Sections A+C+D, regulated** |
| 🇳🇿 "Software engineer, 5yr Python" | 261313 SW Engineer (HIGH) | 20 NZ candidates considered |

**Files:**
- NEW `/app/backend/core/scrapers/quebec_immigration.py` — 250-line PSTQ classifier
- NEW `/app/backend/tests/test_phase107_quebec_and_multi_country.py` — 13 tests
- NEW `/app/frontend/src/pages/sales/components/AtlasAutoSuggestModal.jsx` — Multi-country UI modal
- MOD `/app/backend/routers/sales_ai_helpers.py` — country-aware auto-suggest (140 lines refactored)
- MOD `/app/backend/routers/anz_intel.py` — quebec scraper endpoint + atlas verify exposes quebec_eligibility
- MOD `/app/frontend/src/pages/sales/steps/Step3Profile.jsx` — new button + modal wiring

**Total Phase 10 scrapers:** **11** (7 AU + 6 CA: NOC Canada · IRCC EE Streams · 11 PNPs · IRCC Round Cutoffs · AIP+RCIP+FCIP · **Quebec**)
**Total Phase 10 tests:** **64 passing** (Phase 10.1-10.7)


### 🌍 Migration Atlas — Country-Separated Views + Dry-Run Bug Fix (Jun 8, 2026)
**Status:** ✅ COMPLETE — both issues Sir reported are resolved.

**Issue 1 (CRITICAL BUG):** Dry-Run Preview button was failing on all 5 new CA scrapers because `runEndpointForId()` only had a hard-coded mapping for the original 7 AU scrapers.

**Fix:** Rewrote `runEndpointForId` to read directly from `s.run_endpoint` returned by the backend (with the original 7-mapping kept as a fallback). Now any newly-added scraper auto-works without frontend changes — future-proof.

**Issue 2 (UX):** Sir said: "Migration atlas must have all countries Atlas information separately. AU, CA, NZ should not be merged."

**Fix:** Restructured `AnzIntelAudit.jsx` with **country tabs at the top**:
- 🇦🇺 Australia (932 occupations) · 🇨🇦 Canada (516 occupations) · 🇳🇿 New Zealand (20 occupations)
- Active country highlighted with teal background + raised shadow
- Switching country re-fetches everything country-scoped
- Hero stats now show **CA 5-digit NOCs** / **CA NOC 2021** for CA, or **ANZSCO 4-digit Groups** / **AU 6-digit Records** for AU
- Reference benchmark link auto-switches: `statcan.gc.ca` for CA, `anzscosearch.com` for AU, `immigration.govt.nz` for NZ
- **Tabs auto-hide:** Per-Occupation Heatmap, Orphan 4-digit Groups, and Step 3 — Data Merge are only shown for AU (they don't apply to CA/NZ)
- **Step 4 — Scrapers tab:** Now filters by country. Header shows "(5 for CA)" or "(7 for AU)" with count.
- **Coverage tab:** AU shows full field-coverage heatmap; CA/NZ show a summary card with "Detailed field-coverage will be added in next phase" placeholder

**Backend Changes:**
- `routers/anz_intel.py` → `/scrapers/list` now auto-tags all scrapers without a `country` field as `country: "AU"` (defaults the legacy 7 AU scrapers; new CA scrapers already tagged)

**Frontend Changes:**
- `pages/admin/AnzIntelAudit.jsx`:
  - `selectedCountry` state at top (default 'AU')
  - 3 prominent country tabs with flag + name + occupation count
  - `fetchAll` uses `selectedCountry` param
  - `useEffect` re-fetches when `selectedCountry` changes
  - Hero stats now country-aware (`countryTotals[selectedCountry]`)
  - Reference benchmark URL auto-switches per country
  - Tab list filters out AU-only tabs when CA/NZ selected
  - New `<CoverageCAorNZ>` component for CA/NZ summary placeholder
  - `ScrapersTab` accepts `country` prop and uses `filteredScrapers` (filters by `s.country === country`)
  - Dry-Run fix: `runEndpointForId` reads from backend metadata directly
  - Commit confirmation messages added for all 5 CA scrapers (Hinglish, respectful)
  - Generic CA fallback added to `ScraperDryRunPreview` so any future CA scraper auto-renders stats

**Live Verification:**
- 🇦🇺 AU tab: Hero stats show 1236 ANZSCO 4-digit + 932 AU + 4 verified + 34 drafts + 247 with-child + 989 orphans (all 6 tiles)
- 🇨🇦 CA tab: Hero stats show 516 CA NOCs + 0 verified + 516 drafts (3 tiles, no AU-irrelevant ones)
- 🇨🇦 CA Scrapers tab: only 5 CA scrapers visible (NOC Canada / IRCC EE Streams / Canada PNP / IRCC Round Cutoffs / AIP-RCIP-FCIP)
- 🇨🇦 Dry-Run NOC Canada: Returns 516 unit groups, 0 to create, 0 to update, 516 unchanged (perfect idempotency)

**Files:**
- MOD `/app/backend/routers/anz_intel.py` — auto-tag scrapers with country=AU default
- MOD `/app/frontend/src/pages/admin/AnzIntelAudit.jsx` — country tabs + per-country state + filtered scrapers + generic dry-run preview fallback

### 🇨🇦 Phase 10.4 + 10.5 + 10.6 — IRCC Round Cutoffs, Regional Pilots & Atlas Verify CA UI (Jun 8, 2026)
**Status:** ✅ COMPLETE — 13/13 new pytest PASS · 51/51 Phase 10 regression PASS · Atlas Verify Card UI live with CA-aware tabs.

Sir's ask: "Phase 10.4 IRCC Round Cutoffs + 10.5 AIP/RCIP/FCIP + 10.6 Atlas Verify Card UI for CA".

---

**Phase 10.4 — IRCC Round Cutoff Tracker (2026 H1 program year)**

13 categories tracked, 10 with active cutoffs:
| Category | Latest CRS Min | Draw Date | ITAs |
|----------|---------------:|-----------|------|
| CEC only | 518 | 2026-04-09 | 6,500 |
| PNP only | 749 | 2026-04-02 | 825 |
| Healthcare | 467 | 2026-02-20 | 5,500 |
| Trades | 477 | 2026-04-02 | 2,400 |
| French language | 409 | 2026-03-26 | 3,500 |
| STEM | 491 | 2025-12-04 | 3,000 |
| Education | 479 | 2025-11-15 | 1,800 |
| Transport | 435 | 2025-08-26 | 1,500 |
| Senior Mgrs (CA exp) | 429 | 2026-03-05 | 200 |
| Physicians (CA exp) | **169** | 2026-02-19 | 400 |
| General (all-program) | — | — paused | — |
| Researchers (CA exp) | — | — new category | — |
| Military Recruits | — | — new category | — |

Storage: singleton in `kb_settings` + per-NOC tags showing applicable categories.

---

**Phase 10.5 — AIP + RCIP + FCIP Regional Pilots**

Equivalent to AU's DAMA + ILA (regional/special-route programs):

| Pilot | Provinces / Communities | Priority NOC Tags |
|-------|------------------------|---------------------|
| **AIP** (Atlantic Immigration Program) | NB · NS · PE · NL (4 provinces) | 19 priority NOCs (Healthcare, Education, Trades, IT) |
| **RCIP** (Rural Community Immigration Pilot) | 14 communities across NS/ON/MB/SK/AB/BC | 5-7 NOCs per community |
| **FCIP** (Francophone Community Immigration Pilot) | 6 communities (NB/ON/MB/BC) | French NCLC 5+ required |

**Note (RNIP → RCIP/FCIP):** The old Rural & Northern Immigration Pilot was replaced in 2025 by these two newer pilots. RCIP + FCIP are the active 2026 programs.

**14 RCIP communities seeded:**
Pictou County (NS) · North Bay · Sudbury · Timmins · Sault Ste Marie · Thunder Bay (ON) · Steinbach · Altona/Rhineland · Brandon (MB) · Moose Jaw (SK) · Claresholm (AB) · West Kootenay · North Okanagan Shuswap · Peace Liard (BC)

**6 FCIP communities seeded:**
Acadian Peninsula (NB) · Sudbury · Timmins · Superior East (ON) · St. Pierre Jolys (MB) · Kelowna (BC)

(Sudbury + Timmins are dual-listed in BOTH RCIP & FCIP)

---

**Phase 10.6 — Atlas Verify Card UI (CA-aware)**

`AtlasVerifyCard.jsx` now accepts a `country` prop (default 'AU') and renders:

For **AU**: existing layout (SkillSelect Tier, VETASSESS, State Matrix, Min Invitation Pts, DAMA, ILA)

For **CA** (NEW sections):
1. **TEER + Verification Badge** in header (e.g., "NOC 31301 · TEER 1 · University degree")
2. **🇨🇦 IRCC Federal Programs** card with 3 program tiles: FSWP / CEC / FSTP (each green checkmark or grey X)
3. **🏷️ Category-Based Selection** chips with icons: 🇫🇷 French · 🏥 Healthcare · 🔬 STEM · 🔧 Trade · 📚 Education · ✈️ Transport · 👨‍⚕️ Physicians-CA · 💼 Sr Mgrs-CA · 🧪 Researchers-CA · 🪖 Military
4. **📊 IRCC 2026 Round Cutoffs** grid showing per-category latest CRS min + draw date
5. **🗺️ Provincial Nominee Programs** — per-province cards with stream pills (✨ = EE-linked stream)
6. **🌟 Regional Pilots — AIP · RCIP · FCIP** — pill list with province codes + sector tags + French NCLC requirement

Header: code shown as "NOC 31301" instead of "ANZSCO …".
Footer: source attribution updated to "statcan.gc.ca · canada.ca/express-entry · 11 PNPs · IRCC pilots".

Step3Profile.jsx now passes `country={data.occupation_country || 'AU'}` to AtlasVerifyCard.

**Live verification (Atlas Verify CA 31301 — Registered Nurse):**
- ✅ TEER 1 · University degree
- ✅ FSWP+CEC eligible · FSTP not (correct — RN is not trade)
- ✅ Categories: French + Healthcare
- ✅ 5 Round Cutoffs surfaced (CEC 518, PNP 749, French 409, Healthcare 467)
- ✅ 8 PNPs eligible (BC, AB, SK, MB, NB, PE, NL, NT)
- ✅ 20 Regional Pilots: AIP (4 Atlantic provinces) + 13 RCIP + 6 FCIP

---

**Backend files modified/added:**
- NEW `/app/backend/core/scrapers/ircc_round_cutoffs.py` — 13-category cutoff tracker
- NEW `/app/backend/core/scrapers/ca_regional_pilots.py` — AIP + 14 RCIP + 6 FCIP seed
- NEW `/app/backend/tests/test_phase104_105_cutoffs_and_pilots.py` — 13 tests
- MOD `/app/backend/routers/anz_intel.py` — 2 new scraper endpoints + scrapers/list updated + Atlas Verify exposes new fields

**Frontend files modified:**
- MOD `/app/frontend/src/pages/sales/components/AtlasVerifyCard.jsx` — country-aware rendering + 4 new CA sections + new lucide icons
- MOD `/app/frontend/src/pages/sales/steps/Step3Profile.jsx` — passes country prop to AtlasVerifyCard

**Test coverage (Phase 10 cumulative):**
- 10.1: 9 tests · 10.2: 15 tests · 10.3: 14 tests · 10.4 + 10.5: 13 tests = **51 total passing**


### 🇨🇦 Phase 10.3 — 11 PNP Scrapers + AI Auto-Suggest (Jun 8, 2026)
**Status:** ✅ COMPLETE — 14/14 new pytest PASS · 38/38 Phase 10 regression PASS.

Sir's ask: "11 PNP scrapers + AI Auto-Suggest enhancement".

**Part A — 11 PNPs Registered:**

| # | Code | Province | PNP Name | Streams | Priority NOCs |
|---|------|----------|----------|---------|---------------|
| 1 | BC | British Columbia | BC PNP | 5 | 66 |
| 2 | ON | Ontario | OINP | 7 | 13 |
| 3 | AB | Alberta | AAIP | 6 | 28 |
| 4 | SK | Saskatchewan | SINP | 5 | 11 |
| 5 | MB | Manitoba | MPNP | 4 | 11 |
| 6 | NB | New Brunswick | NBPNP | 4 | 11 |
| 7 | NS | Nova Scotia | NSNP | 5 | 17 |
| 8 | PE | Prince Edward Island | PEI PNP | 3 | 7 |
| 9 | NL | Newfoundland & Labrador | NLPNP | 4 | 5 |
| 10 | YT | Yukon | YNP | 4 | 4 |
| 11 | NT | Northwest Territories | NTNP | 4 | 9 |
| | **Totals** | | | **51 streams** | **182 unique priority NOC tags** |

(Quebec excluded — runs separate PEQ/PSTQ system)

**Highlight streams seeded with verified 2026 occupation lists:**
- **BC PNP Skills Immigration — Technology**: 35 NOCs (per official May 28 2026 program guide)
- **BC PNP Skills Immigration — Healthcare**: 31 NOCs (nurses, physicians, dentists, allied health)
- **OINP Human Capital Priorities**: 6 tech NOCs (per Ontario tech draws)
- **OINP In-Demand Skills**: TEER 4-5 priority occupations (warehousing, agriculture, construction labour)
- **AAIP Accelerated Tech Pathway**: 17 tech NOCs
- **NS Critical Construction Worker Pilot**: 14 trade NOCs

**Live verification (sample):**
- **21231 Software Engineer** → eligible across **7 provinces** (BC/ON/AB/SK/MB/NB/NL)
- **72310 Carpenter** → eligible in **NS Critical Construction** + others
- **31301 Registered Nurse** → eligible in **8 provinces** (BC/AB/SK/MB/NB/PE/NL/NT)
- **62200 Chef** → eligible in **5 provinces** (AB/MB/NB/PE/NT)

**Part B — AI Auto-Suggest Endpoint (NEW):**

`POST /api/sales/ai/atlas-auto-suggest`

Hybrid LLM Router routes this task to **Haiku 4.5** (registered as `atlas_auto_suggest` in `ai_models.py` — fast + cheap).

Input:
```json
{
  "description": "Backend software engineer, 8 years Python distributed systems experience",
  "province_code": "BC",  // optional
  "max_suggestions": 3
}
```

Output (live response):
```json
{
  "suggestions": [
    {
      "code": "21231",
      "title": "Software engineers and designers",
      "confidence": "high",
      "reasoning": "Backend engineer is explicitly listed in alt titles...",
      "destination_province_match": true,
      "atlas": {
        "teer_category": 1,
        "teer_label": "University degree",
        "ee_eligibility": {
          "fswp_eligible": true,
          "cec_eligible": true,
          "fstp_eligible": false,
          "categories": ["french_language"]
        },
        "pnp_eligibility": [
          {"province_code": "BC", "streams": [{"name": "Skills Immigration — Technology"}], ...},
          {"province_code": "ON", "streams": [{"name": "Human Capital Priorities (HCP)"}], ...},
          ...
        ]
      }
    }
  ],
  "tip": "Backend engineers in fintech are highly sought in BC; emphasize distributed systems...",
  "_ai_model": "claude-haiku-4-5-20251001",
  "_province_filter": "BC"
}
```

**Demo flows tested live:**
- **"Baker → Manitoba"** → returns 63202 Bakers (HIGH), Sales tip: "emphasize commercial production scale"
- **"Tech → BC"** → returns 21231 + 21230 (both HIGH), BC PNP sorted first in eligibility
- **"Indian chef, 12yr, 5-star hotels"** → 62200 Chefs (HIGH) + 63200 Cooks (MEDIUM, 5 PNPs), human-quality tip
- **"Nurse, 6yr ICU"** → 31301 RN (HIGH) with 8 PNPs eligible + Healthcare category

**Files:**
- NEW `/app/backend/core/scrapers/pnp_canada.py` — 330-line PNP registry + idempotent applier
- NEW `/app/backend/tests/test_phase103_pnp_and_auto_suggest.py` — 14 tests
- MOD `/app/backend/routers/sales_ai_helpers.py` — added `/atlas-auto-suggest` endpoint (~120 lines)
- MOD `/app/backend/core/ai_models.py` — `atlas_auto_suggest` → Haiku 4.5
- MOD `/app/backend/routers/anz_intel.py` — new scraper endpoint + scrapers/list entry + Atlas Verify now exposes `pnp_eligibility`

**Total Phase 10 backend tests: 38 passing (10.1: 9 + 10.2: 15 + 10.3: 14)**


### 🇨🇦 Phase 10.2 — IRCC Express Entry Streams Classifier (Jun 8, 2026)
**Status:** ✅ COMPLETE — 15/15 pytest PASS · 45/45 regression PASS (no breakage in Phase 9).

Sir's ask: "FSWP/CEC/FSTP + 10 Category-Based Selection per NOC (2026 official IRCC list)".

**Data Source:** IRCC official — https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations/category-based-selection.html (scraped 2026-03-31 edition)

**Eligibility Rules Implemented (Deterministic — no AI/scrape):**

A) **Federal Programs:**
- **FSWP** (Federal Skilled Worker Program) — TEER 0/1/2/3 → 376 of 516 CA codes eligible
- **CEC** (Canadian Experience Class) — TEER 0/1/2/3 + 1yr Canadian exp → 376 eligible
- **FSTP** (Federal Skilled Trades Program) — Major Groups 72/73/82/83/92/93 + TEER 2-3 only → 98 eligible

B) **Category-Based Selection 2026 (10 categories, exact counts match official IRCC tables):**
| # | Category | NOCs | Notes |
|---|----------|------|-------|
| 1 | French-language proficiency | 376 (all FSWP-eligible) | NCLC 7+ required, not NOC-specific |
| 2 | Healthcare and social services | **37** | Physicians, nurses, allied health, social workers |
| 3 | STEM | **11** | Cybersecurity, eng disciplines, eng technologists, insurance agents |
| 4 | Trade occupations | **25** | Construction mgrs, machinists, electricians, plumbers, carpenters, etc. |
| 5 | Education | **5** | Teachers, ECEs, classroom assistants |
| 6 | Transport | **4** | Aircraft mechs, pilots, avionics, auto techs |
| 7 | Physicians (Canadian exp) | **3** | NOCs 31100/31101/31102 — CA work exp required |
| 8 | Senior Managers (Canadian exp) | **4** | NOCs 00012-00015 — CA work exp required |
| 9 | Researchers (Canadian exp) | **2** | University profs, post-secondary asst — CA work exp required |
| 10 | Skilled Military Recruits | **3** | NOCs 40042/42102/43204 — CAF offer + 10yr foreign mil svc |

**❌ Removed in 2026:** Agriculture and agri-food (was 5th category in 2024-25, no longer in 2026 official list)

**Backend additions:**
- `core/scrapers/ircc_ee_streams.py` — pure-Python deterministic classifier
  - `CATEGORY_REGISTRY` — UI metadata (icon, label, requires_canadian_exp flag)
  - `_CATEGORY_NOC_MAP` — NOC lookup sets per category (baked from IRCC official 2026 tables)
  - `classify(code, teer)` — returns full payload for a single NOC
  - `apply_to_db(db, dry_run, actor)` — bulk-tag all CA records, idempotent

- `routers/anz_intel.py`:
  - `POST /api/anz-intel/scrapers/ircc-ee-streams/run?dry_run=` (admin-only)
  - `/scrapers/list` updated → 9 scrapers ready (was 8, now incl. CA EE streams)
  - `/verify/{code}` Atlas Verify endpoint now:
    - Accepts 5-digit (CA NOC) OR 6-digit (AU/NZ ANZSCO) with country-aware validation
    - Returns new fields: `teer_category`, `teer_label`, `ee_eligibility`, `hierarchy`

**Live Verification (sample spot-checks):**
- **21231 Software engineers** (TEER 1) → FSWP+CEC ✓, French only (NOT in STEM 2026 ❌)
- **31102 Family physicians** (TEER 1) → FSWP+CEC ✓ + Healthcare + Physicians-CA-exp (3 categories!)
- **21300 Civil engineers** (TEER 1) → FSWP+CEC ✓ + STEM ✓
- **72310 Carpenters** (TEER 2) → FSWP+CEC+FSTP ✓ + Trade ✓ (all 4!)
- **40042 CAF Officers** (TEER 0) → FSWP+CEC ✓ + Military Recruits ✓
- **85100 Labour TEER 5 sample** → ALL programs FALSE, no categories (correctly excluded)

**Idempotency:** 2nd commit → 0 updated, 516 skipped_unchanged ✅

**Tests added (`tests/test_phase102_ircc_ee_streams.py` — 15 tests):**
1. `test_classify_software_engineer` — SW eng NOT in STEM 2026 list (subtle correctness)
2. `test_classify_family_physician_multi_category` — multi-category match
3. `test_classify_civil_engineer_stem` — STEM eligible
4. `test_classify_carpenter_fstp_trade` — FSTP + Trade dual-tag
5. `test_classify_military_recruit` — Military category
6. `test_classify_high_school_only_excluded_from_fswp` — TEER 5 excluded
7. `test_classify_senior_managers_ca_exp` — All 4 senior mgr codes
8. `test_scrapers_list_includes_ircc_ee_streams` — endpoint exposed
9. `test_ircc_ee_streams_dry_run_matches_official_2026_counts` — exact IRCC counts (37/11/25/5/4/3/4/2/3)
10. `test_ircc_ee_idempotent` — 0 updates on re-run
11. `test_ircc_ee_partner_blocked` — RBAC enforced
12. `test_category_registry_completeness` — every category has metadata
13. `test_agriculture_removed_per_2026` — confirm 2026 removal
14. `test_atlas_verify_ca_surfaces_ee_eligibility` — Atlas Verify endpoint integration
15. `test_atlas_verify_rejects_wrong_length_for_country` — AU 6-digit, CA 5-digit validation

**Files:**
- NEW `/app/backend/core/scrapers/ircc_ee_streams.py` — 280-line deterministic classifier
- NEW `/app/backend/tests/test_phase102_ircc_ee_streams.py` — 15 tests
- MOD `/app/backend/routers/anz_intel.py` — new scraper endpoint + scrapers/list entry + verify endpoint country-aware


### 🇨🇦 Phase 10.1 — Canada NOC 2021 V1.0 Bulk Importer (Jun 8, 2026)
**Status:** ✅ COMPLETE — 9/9 pytest PASS · UI verified live (Smart Sales Helper shows 516 CA codes).

Sir's ask: Start Canada Atlas build (mirror of AU Phase 9.1).

**Data Source:**
- Statistics Canada NOC 2021 V1.0 (official, current) — https://www.statcan.gc.ca/en/subjects/standard/noc/2021/indexV1
- Direct CSV download: `noc-2021-v1.0-classification-structure.csv` (384 KB) + `noc-2021-v1.0-elements.csv` (4.89 MB)
- Stored locally at `/app/backend/data/noc_2021/` (no network calls on every run)

**NOC 2021 Hierarchy (5-level, 5-digit codes):**
- 10 Broad Categories · 45 Major Groups · 89 Sub-major Groups · 162 Minor Groups · **516 Unit Groups**
- TEER (Training/Education/Experience/Responsibility) = 2nd digit of 5-digit code
- TEER 0 = Mgmt · 1 = University · 2 = College/apprenticeship 2+yrs · 3 = College <2yrs · 4 = High school · 5 = Short-term

**Backend additions:**
- `core/scrapers/noc_canada.py` — pure-Python CSV parser + idempotent upsert
  - Reads structure CSV → 516 unit groups with title + class definition
  - Reads elements CSV (44,037 rows) → enriches each code with alternative titles (up to 30), main duties (up to 25), employment requirements, exclusions, additional info
  - Computes hierarchy chain (broad → major → sub-major → minor → unit) for breadcrumbs
  - Idempotency: only "scraper-owned" fields are refreshed; `status`/`verification`/`linked_product_id`/`custom_qa`/`assessing_authority` are preserved across re-runs
  - Timestamp fields (`updated_at`, `last_enriched_at`) excluded from change-detection so 2nd run shows 516 skipped_unchanged
- `routers/anz_intel.py`:
  - `POST /api/anz-intel/scrapers/noc-canada/run?dry_run=` (admin-only)
  - `/scrapers/list` updated → 8 scrapers ready (was 7)
  - `/audit-summary` totals now include CA + NZ counts (was AU-only)

**Live verification:**
- Dry-run: 486 to create + 30 to update (existing legacy migration) = 516 total
- Commit: 486 inserted + 30 updated successfully
- Idempotency: 2nd commit → 0 changes, 516 skipped_unchanged
- TEER distribution: TEER 0=48, 1=97, 2=162, 3=69, 4=95, 5=45 (sums to 516)
- Sample 21231 (Software engineers and designers): TEER 1 (University degree) + 30 alt titles + 7 typical_tasks + major group "Professional occupations in natural and applied sciences"

**Smart Sales Helper integration:**
- ✅ `/api/sales/occupations/search?country=CA` returns 516 codes immediately (no sync needed — Atlas + Sales share `occupation_master`)
- ✅ `/typeahead?q=software&country=CA` correctly ranks: 21231 (88%) → 21232 (88%) → 21311 (88%) → 22222 (60%)
- ✅ Partner Portal → Smart Sales Helper → CA filter → all 516 cards render with NOC code, title, TEER level, alt titles, federal/WES badges

**Tests added (`tests/test_phase101_noc_canada.py`):**
1. `test_scrapers_list_includes_noc_canada` — exposed in `/scrapers/list` with country=CA + estimated_records=516
2. `test_noc_canada_dry_run_reports_516` — dry-run returns 516 unit groups + TEER distribution covers 0-5
3. `test_noc_canada_idempotent_after_commit` — 2nd run = 0 created/updated, 516 skipped_unchanged
4. `test_noc_canada_partner_blocked` — RBAC enforced (partner gets 403)
5. `test_sales_search_returns_516_ca_codes` — Sales API correctly exposes all 516
6. `test_known_software_engineer_noc_21231` — typeahead returns the famous SW engineer code
7. `test_audit_summary_now_includes_ca_totals` — totals expose CA aggregate
8. `test_noc_data_files_exist` — CSV files shipped with repo
9. `test_teer_label_helper` — TEER 0-5 → human labels

**Files:**
- NEW `/app/backend/core/scrapers/noc_canada.py` — importer module
- NEW `/app/backend/data/noc_2021/noc-2021-v1.0-classification-structure.csv` — 822 rows (10+45+89+162+516)
- NEW `/app/backend/data/noc_2021/noc-2021-v1.0-elements.csv` — 44,037 rows
- NEW `/app/backend/tests/test_phase101_noc_canada.py` — 9 tests
- MOD `/app/backend/routers/anz_intel.py` — new scraper endpoint + scrapers/list entry + audit-summary CA/NZ totals

**Next:** Phase 10.2 will map each NOC to IRCC Express Entry streams (FSWP / CEC / FSTP) using TEER eligibility rules.


### 🔧 Phase 9 Comprehensive Regression Test (Jun 8, 2026)
**Status:** ✅ **61/61 Phase 9 pytest PASS** · UI smoke verified on Atlas Audit + Calculator Rules Editor.

Sir requested end-to-end Phase 9.1→9.9 regression with Expected-vs-Actual outcomes.

**Bug fix shipped during regression:**
- `routers/anz_intel.py` audit-summary `TRACKED_FIELDS` had stale Phase 9.5 field names (`latest_invitation_min_points`, `dama_inclusion`, `ila_inclusion`). DB actually stores them as `min_invitation_points`, `dama_eligibility`, `ila_eligibility`. Fixed mapping in `TRACKED_FIELDS`, `_humanize`, `_source_hint`.
- Result: Field coverage went from "0/0/0" (broken) → **Min Invitation Pts 39.7% · DAMA 1.7% · ILA 1.0%** (correct).

**Test outcome summary:**
| Phase | Test File | Tests | Status |
|-------|-----------|-------|--------|
| 9.1 + 9.2 | test_phase9_scrapers.py | 12 | ✅ PASS |
| 9.4 | test_phase94_calculator_bugs.py | 5 | ✅ PASS |
| 9.5 | test_phase95_dama_ila_invitation.py | 9 | ✅ PASS |
| 9.6 | test_phase96_rules_engine.py | 11 | ✅ PASS |
| 9.7 | test_phase97_rules_wiring.py | 6 | ✅ PASS |
| 9.8 | test_phase98_ca_nz_rules.py | 10 | ✅ PASS |
| 9.9 | test_phase99_edit_history_biometric.py | 8 | ✅ PASS |
| **TOTAL** | — | **61** | ✅ **100%** |


### 🔏 Phase 9.9 — Edit History tab per PA + Biometric E-sign Packet (Jun 8, 2026)
**Status:** ✅ COMPLETE — 8/8 pytest PASS. Code linted clean.

Sir's ask: "Edit History tab + Biometric E-sign packet for legal disputes."

**Backend changes:**
- `routers/pre_assessment.py` — NEW `GET /api/pre-assessment/{pa_id}/edit-history` returns aggregated timeline from `audit_logs` + agreement sign events + biometric capture markers.
- `routers/agreement_templates.py` — `POST /pa-agreements/{aid}/sign` body schema extended with `biometric_packet: Optional[dict]`. Persists to `pa_signatures.biometric_packet`. NEW `GET /pa-agreements/{aid}/signature-forensics` (admin/case_manager only).
- `routers/proposal_docs.py` — `POST /proposal-docs/{pa_id}/esign` also accepts `biometric_packet`.

**Frontend changes:**
- `components/SignatureCanvas.jsx` — captures device fingerprint (user-agent, screen, timezone), GPS (optional), drawing path (mouse/touch coords + timestamps), canvas fingerprint hash.
- `components/pa/PaEditDetailsModal.jsx` — new "Edit History" tab showing chronological audit timeline with actor/action/timestamp/biometric badge.
- `components/ClientAgreementSigning.jsx` — passes biometric packet to esign endpoint.

**Test coverage:**
- Edit history returns timeline for known PA + 404 on unknown + partner access scoped to own PA
- Signature forensics endpoint role-gated (partner blocked, admin 404 on unknown agreement)
- Schema accepts biometric_packet field (no 422) on both `/pa-agreements/.../sign` and `/proposal-docs/.../esign`
- Biometric field is optional (backwards compatible with old clients)


### 🌐 Phase 9.8 — CA + NZ Calculators Wired to Rules Engine (Jun 7, 2026)
**Status:** ✅ COMPLETE — 10/10 new wiring tests PASS · 107/107 total regression PASS · UI verified for all 3 countries.

Sir's ask: "CA + NZ calculators ko bhi rules-engine se wire kar do".

**Backend changes (`core/sales_calculator.py`):**

*Canada (`calculate_ca_crs`):*
- Signature now accepts `rules: Optional[Dict] = None`
- 7 hardcoded "Additional Points" values now route through `_lookup_named_item(rules, "additional", ...)`:
  - `provincial_nomination` (default 600)
  - `job_offer_noc_00` (200) · `job_offer_noc_0_a_b` (50)
  - `canadian_education_3plus_years` (30) · `canadian_education_1_2_years` (15)
  - `sibling_in_canada` (15) · `french_clb_7` (50)
- Core IRCC tables (age 17-99, education, language CLB, work experience, transferability) remain hardcoded — these have with/without-spouse variants and are rarely overridden

*New Zealand (`calculate_nz_smc`):*
- Signature now accepts `rules: Optional[Dict] = None`
- All hardcoded values now route through rules engine lookups:
  - Age bands (4 ranges) → `_lookup_band_points("age", ...)`
  - Qualification (PhD/Master/Bachelor/Diploma) → `_lookup_category_points("qualification", ...)`
  - Skilled employment years (6 bands) → `_lookup_band_points("skilled_employment_years", ...)`
  - Extras (job_offer, skilled_employment_current, regional, partner_skilled_master) → `_lookup_named_item("extras", ...)`

**Rules engine defaults updated (`core/rules_engine.py`):**
- NZ defaults now include `age` table (was missing) so admins see + can edit it in Rules Editor
- NZ `qualification` defaults clarified (Master=50, was Master=70 — corrected to match the calculator code)
- NZ `skilled_employment_years` bands updated to match calculator (2-3:5, 4-5:10, 6-7:15, 8-9:20, 10+:30)

**Master dispatcher updated:**
```python
if c == "CA": return calculate_ca_crs(profile, with_spouse, rules=rules)
if c == "NZ": return calculate_nz_smc(profile, rules=rules)
```
Both now receive admin overrides via `calculate_with_rules()` wrapper that already exists.

**Tests added (`tests/test_phase98_ca_nz_rules.py`):**
1. `test_ca_baseline_with_pnp` — PNP +600 confirmed in defaults
2. `test_ca_pnp_override_to_999` — admin override flows through
3. `test_ca_job_offer_override` — NOC 00 200→50 + NOC 0/A/B 50→25 both verified
4. `test_ca_french_and_sibling_overrides` — French 50→100 + Sibling 15→30
5. `test_nz_baseline_no_extras` — 25yo Master 5yr = 90 baseline confirmed
6. `test_nz_age_override_changes_score` — age 20-29 30→99 flows through
7. `test_nz_qualification_override` — Master 50→80 verified
8. `test_nz_work_experience_band_override` — 4-5yr band 10→25 verified
9. `test_nz_job_offer_extra_override` — job offer 30→80 verified
10. `test_nz_partner_master_override` — partner master 20→50 verified

**UI verification:**
- Calculator Rules Editor → Switch to CA → CRS tables (age/language/education/additional) all rendered with proper IRCC values
- Switch to NZ → New age bands table now visible (was missing before), qualification + skilled_employment_years + extras all editable
- All overrides save to `kb_settings.calculator_rules_{country}` and immediately affect live calculator output

**Coverage summary post-9.8:**
| Country | Override-able tables | Hardcoded (rare overrides) |
|---------|---------------------|----------------------------|
| AU      | age, english, education, overseas_experience, australia_experience, partner_skills, bonuses (5 named), state_nomination | — (all wired) |
| CA      | additional (7 named: PNP, French, Sibling, Job offers, CA education) | age, education, language CLB, work experience, transferability |
| NZ      | age, qualification, skilled_employment_years, extras (4 named: job_offer, skilled_employment, regional, partner_master) | — (all wired) |


### ⚡ Phase 9.7 — Calculator Wired to Rules Engine + Haiku Cost Optimization (Jun 7, 2026)
**Status:** ✅ COMPLETE — 6/6 new wiring tests PASS · 43/43 total regression PASS · UI verified live end-to-end.

#### Task 1 — Calculator now consumes `rules_engine.load_rules()` (admin overrides flow through end-to-end)

The Phase 9.6 foundation was infrastructure-only — calculator still used hardcoded constants. Phase 9.7 wires the actual point-lookups to read from `kb_settings.calculator_rules_<country>` documents with fallback to hardcoded baselines.

**Backend changes (`core/sales_calculator.py`):**
- 5 new lookup helpers — `_lookup_band_points`, `_lookup_tier_points`, `_lookup_category_points`, `_lookup_named_item`, `_lookup_subclass_points`
- `calculate_au_points()` + `_au_partner_skills()` now accept optional `rules=None` parameter; all 13 hardcoded point values (age bands, english tiers, education categories, experience bands, 5 bonus values, 2 state-nomination subclass values, 4 partner-skills categories) route through lookups
- New async wrapper `calculate_with_rules(db, profile, country, visa_subclass)` — loads override from DB, calls calculator, attaches `rules_source` + `rules_version` to response
- **Behavior preserved**: when no override exists OR partial override is set, untouched tables still use hardcoded defaults (verified by `test_partial_override_other_tables_use_defaults`)

**Routers updated to call `calculate_with_rules()`:**
- `routers/sales_calculator.py` — `/sales/calculator/calculate` + `/calculate-batch`
- `routers/sales_wizard_v2.py` — `/sales/wizard/calculate-parallel`
- `routers/sales_assessments.py` — assessment save + re-calc endpoints

**End-to-end live verification:**
- Saved override: `english.tiers.proficient = 999` via Admin Rules Editor → calculator immediately returned new score (no restart)
- Reset → score back to baseline 75
- Partial override (only age bands changed) → other tables still on defaults

#### Task 2 — Haiku 4.5 wired to `step_document_helper` + `ai_intelligence_quick`

- `routers/step_documents.py:_call_ai()` now uses `model_for("step_document_helper")` → Haiku 4.5
- `routers/ai_intelligence.py:_call_gpt()` now uses `model_for("ai_intelligence_quick")` → Haiku 4.5
- ~73% cost reduction on these high-frequency, low-stakes calls (per Anthropic pricing)
- Quality-critical features (resume parsing, proposal generation, country guides, KB polishing, eligibility reasoning, admin AI-Extract) stay on Sonnet 4.6

**Model registry status (`core/ai_models.py`):**
| Task                        | Model      | Why |
|----------------------------|------------|-----|
| occupation_suggester       | Haiku 4.5  | typeahead-style suggestions, high frequency |
| step_document_helper       | Haiku 4.5  | quick doc hints |
| ai_intelligence_quick      | Haiku 4.5  | short helper outputs |
| resume_extractor           | Sonnet 4.6 | multi-section extraction |
| proposal_standard          | Sonnet 4.6 | client-facing |
| country_guide              | Sonnet 4.6 | long-form |
| kb_ai_polish               | Sonnet 4.6 | quality-critical |
| ai_verification            | Sonnet 4.6 | mission-critical |
| ai_workflow_builder        | Sonnet 4.6 | multi-step plans |
| eligibility_reasoning      | Sonnet 4.6 | mission-critical |
| ai_extract_admin           | Sonnet 4.6 | high-stakes |
| proposal_premium           | Opus 4.6   | premium tier |

**Tests added (`tests/test_phase97_rules_wiring.py`):**
1. `test_default_baseline_score` — confirms baseline 75 with no override + `rules_source = "hardcoded_defaults"`
2. `test_override_age_band_changes_score` — age band 30 → 99 yields total 144 + `rules_source = "db_override"`
3. `test_override_english_tier_changes_score` — proficient 10 → 50 yields total 115
4. `test_override_partner_skills_single_value` — single bonus 10 → 0 yields total 65
5. `test_reset_returns_to_baseline` — POST `/reset` restores baseline 75
6. `test_partial_override_other_tables_use_defaults` — touching only `age` leaves `english`/`education`/`partner` on defaults


### 🧮 Phase 9.6 — Rule-Based Engine + Bulk State AI + DAMA/ILA PDF (Jun 7, 2026)
**Status:** ✅ COMPLETE — 11/11 backend pytest PASS. UI verified via live screenshots.

Sir's ask: "Rule-Based Scoring Engine + VIC/SA/ACT/NT/TAS state nomination AI extract + DAMA/ILA PDF parsing".

#### Task 1 — Calculator Rules Engine (`core/rules_engine.py`)
Admin-configurable scoring tables persisting to `kb_settings.calculator_rules_{country}`. Calculator stays stable (hardcoded fallback). 3 countries supported: AU, CA, NZ.

**Endpoints:**
- `GET /api/anz-intel/calculator-rules/{AU|CA|NZ}` — returns active rules (DB override or hardcoded defaults)
- `PUT /api/anz-intel/calculator-rules/{country}` — saves override
- `POST /api/anz-intel/calculator-rules/{country}/reset` — deletes override → defaults

**Admin UI** (`pages/admin/CalculatorRulesEditor.jsx` at `/admin/calculator-rules`):
- 3 country tabs (🇦🇺🇨🇦🇳🇿) with flag + description
- Active source badge: 🔒 Hardcoded Defaults vs ✏️ DB Override
- Sidebar: list of tables with rule summary + version + last-edit metadata
- Main: live JSON editor with real-time parse-error indicator + Save / Reset
- Production caution panel + Save success toast

**Default rule sets cover:**
- AU: age (5 bands), english (4 tiers), education (8 categories), overseas/AU experience (bands), partner skills (4 categories), bonuses (5 named items), state nomination (per-subclass)
- CA: age (6 bands), language (CLB 4-10), education (PhD-Trade), additional (7 named — PNP/French/Sibling/Job offer/Canadian-edu)
- NZ: qualification, skilled employment years, named extras (NZ job offer / regional / partner)

#### Task 2 — Bulk State Nomination AI Extract (`/ai-extract-state-bulk/{preview,commit}`)
For VIC, SA, ACT, NT, TAS, WA (sites that are JS-driven and don't scrape).

- Body: `{state, source_url, raw_text}` (up to 12,000 chars)
- Claude Sonnet 4.6 extracts array of `{code, title, sc190, sc491, demand, caveats}`
- Smart matching: 6-digit exact OR 4-digit unit-group expansion to all child codes
- Preview shows matched_count / unmatched_count / unit_group_expansions
- Commit merges into `state_territory_eligibility` (replaces existing entry for that state, preserves others)

**Admin UI** (new `BulkStateExtractCard` in Step 5 Manual Tools tab):
- State dropdown (VIC/SA/ACT/NT/TAS/WA/NSW/QLD)
- Source URL field for audit trail
- Large textarea for pasted content
- Preview cards + per-record badges (190/491/demand) + commit button

#### Task 3 — DAMA/ILA PDF Parser (`/dama-pdf/{preview,commit}`)
Admin uploads official DAMA agreement PDF (or ILA PDF) → `pdfplumber` extracts text → regex finds all 6-digit ANZSCO codes → checkbox preview → commit.

- POST with `multipart/form-data` file + query params `target_id` (e.g., `nt`, `aerotropolis`, `restaurant`) + `target_type` (`dama` or `ila`)
- Preview shows PDF pages, codes_extracted, matched_in_db (with `already_tagged_with_target` flag per code), unmatched_codes
- Commit attaches the full DAMA/ILA seed entry (region, state, valid_until, concessions) to selected codes

**Admin UI** (new `DamaIlaPdfCard` in Step 5 Manual Tools tab):
- Type toggle (DAMA / ILA) → dropdown with all 13 DAMAs OR 4 ILAs
- File upload + Extract Codes button
- Per-code checkbox list with status badges (verified/already-tagged)
- Pre-selects all NOT-already-tagged codes
- Commit confirms count + invokes parent refresh

**Tests added (`tests/test_phase96_rules_engine.py`):**
1. `test_get_rules_returns_au_defaults` — defaults load correctly
2. `test_save_and_reload_override` — PUT → GET → reset → GET round-trip
3. `test_rules_supports_au_ca_nz` — all 3 countries
4. `test_rules_rejects_unsupported_country` — 400 on invalid country
5. `test_rules_rbac_partner_blocked` — partner blocked
6. `test_bulk_state_extract_preview_vic` — live AI call extracts ≥3 codes from sample text
7. `test_bulk_state_bad_state_400` — input validation
8. `test_dama_pdf_preview_extracts_codes` — pdfplumber + regex flow
9. `test_dama_pdf_commit_updates_records` — `dama_eligibility` populated post-commit
10. `test_dama_pdf_rejects_invalid_target` — target_type validation
11. `test_dama_pdf_rbac_partner_blocked` — partner blocked

**Files:**
- NEW `/app/backend/core/rules_engine.py` — admin-configurable rules
- MOD `/app/backend/routers/anz_intel.py` — 7 new endpoints (rules GET/PUT/RESET + bulk state preview/commit + dama-pdf preview/commit)
- NEW `/app/frontend/src/pages/admin/CalculatorRulesEditor.jsx`
- MOD `/app/frontend/src/pages/admin/AnzIntelAudit.jsx` — added `BulkStateExtractCard` + `DamaIlaPdfCard` + Calculator Rules Editor link in hero
- MOD `/app/frontend/src/App.js` — new route `/admin/calculator-rules`


### 🚀 Phase 9.5 — Min Invitation Points + DAMA + ILA Scrapers (Jun 7, 2026)
**Status:** ✅ COMPLETE — 9/9 new pytest PASS · 12/12 existing scrapers + verify endpoint tests PASS · UI verified via screenshots.

Sir's ask: "Min Invitation Points scraper + DAMA + ILA scrapers banao".

Each Home Affairs source publishes data behind PDFs or JS-driven UIs (same constraint as VETASSESS). Pragmatic curated-seed approach used, identical to vetassess_groups.py — extensible via existing CSV/AI-Extract tools.

**1. SkillSelect Min Invitation Points (`/api/anz-intel/scrapers/min-invitation-points/run`)**
- Source: https://immi.homeaffairs.gov.au/visas/working-in-australia/skillselect/previous-rounds
- Latest confirmed cutoffs (2025-26):
  - Subclass 189 (standard) = **90 pts**
  - Subclass 189 (Health/Education priority Tier 1) = **65 pts**
  - Subclass 491 (Family-sponsored) = **65 pts**
- Stored in two places: `kb_settings._id='min_invitation_points'` singleton + `occupation_master.min_invitation_points` on all Tier-1/Tier-2 records
- 370 Tier-1/Tier-2 records tagged with `min_invitation_points` payload

**2. DAMA — Designated Area Migration Agreements (`/api/anz-intel/scrapers/dama/run`)**
- Source: https://immi.homeaffairs.gov.au/visas/employing-and-sponsoring-someone/labour-agreements/types-of-labour-agreements/designated-area-migration-agreements-(dama)
- **13 current DAMAs** seeded: NT, Goldfields, FNQ, East Kimberley, Pilbara, SW WA, Orana NSW, Adelaide Tech, SA Regional, Townsville, Hobart City, Great South Coast, Western Sydney Aerotropolis
- Each DAMA stores: region, state, valid_until, concessions (age 55, English IELTS 5.0, salary), sample occupations
- 15 occupations tagged across DAMA regions (e.g., 263111 Network Engineer → Adelaide Tech + Aerotropolis)

**3. ILA — Industry Labour Agreements (`/api/anz-intel/scrapers/ila/run`)**
- Source: https://immi.homeaffairs.gov.au/visas/employing-and-sponsoring-someone/labour-agreements/types-of-labour-agreements/industry-labour-agreements
- **4 industries** seeded:
  - **Restaurant** (Premium Dining): Chef · Cook · Café/Restaurant Manager · Trade Waiter
  - **Meat**: Skilled Meat Worker · Meat Boner and Slicer
  - **Aged Care**: Nursing Support · Personal Care Assistant · Aged/Disabled Carer
  - **Fishing**: Deck Hand · Fishing Hand · Ship's Master · Engineer · Officer · Seafood Process
- Each ILA stores: industry name, visa subclasses (482/186/494), concessions (PR pathway, English, salary, union MoU)
- 9 occupations tagged with ILA eligibility

**Atlas Verify Card UI extended (`pages/sales/components/AtlasVerifyCard.jsx`)**
3 new sections rendered for sales reps:
- 🎯 SkillSelect Min Invitation Points — large numeric cards for 189 + 491(family) cutoffs with program year footnote
- 🗺️ DAMA Eligibility — region cards with state badge, valid-until date, concession pills
- 🏭 ILA Eligibility — industry cards with visa subclass badges + concession pills

**Backend endpoints:**
- `GET /api/anz-intel/scrapers/list` now returns 7 ready scrapers (was 4)
- `GET /api/anz-intel/verify/{code}` returns 3 new fields: `min_invitation_points`, `dama_eligibility`, `ila_eligibility`
- 3 new POST endpoints under `/scrapers/{min-invitation-points,dama,ila}/run`

**Tests (`tests/test_phase95_dama_ila_invitation.py`):**
1. `test_scrapers_list_has_seven` — `/scrapers/list` exposes all 7 ready scrapers
2. `test_min_invitation_points_dry_run` — cutoffs match expected values
3. `test_min_invitation_points_idempotency` — 2nd run does 0 updates
4. `test_dama_dry_run` — 13 DAMAs registered with required fields
5. `test_dama_tags_aerotropolis_for_software_engineer_unit_group` — 263111 gets Aerotropolis after commit
6. `test_ila_dry_run` — 4 industries (restaurant/meat/aged_care/fishing)
7. `test_verify_returns_new_fields` — Atlas verify endpoint includes all 3 new fields
8. `test_partner_blocked_from_dama` — RBAC enforced
9. `test_partner_can_still_read_verify` — sales can read enriched data


### 🎯 Phase 9.4 — Smart Sales Helper Calculator P0 Bug Fixes (Jun 7, 2026)
**Status:** ✅ COMPLETE — 5/5 P0 regression PASS + 54/54 calculator unit tests PASS. UI verified via live screenshot.

Sir's P0 complaints investigated thoroughly. Real-vs-perceived bug breakdown:

| Sir's complaint | Real status after investigation | Fix shipped |
|-----------------|----------------------------------|-------------|
| "Partner 10 pts wrongly shows when SINGLE" | **NOT A BUG** — Single applicants are awarded 10 points per official Home Affairs rules (no-migrating-partner bonus). UX label was misleading. | **Context-aware label** — single now shows "No Migrating Partner Bonus", PR spouse shows "Australian PR Partner Bonus", skilled partner shows "Skilled Partner", etc. |
| "Parallel subclass mismatch" | 🔴 **REAL CRITICAL BUG** — `ParallelSubclassPanel.jsx` read `data.highest_qualification` + `data.lang_overall` but wizard's actual fields are `data.qualification` + `data.ielts_overall` → Parallel scores always had Education=0 + English=0 → mismatch with main calculator | Fixed field-name mapping to read canonical wizard fields. Also added spouse block when applicable. |
| "189/190/491 saath nahi dikh rahe" | Panel was gated by `data.marital_status` truthy + Bug #2 made scores wrong | Removed gate (calculator handles empty marital as single per official rules). Fixed via #2. |
| "Re-save points drift" | Drift was downstream of Bug #2 field-name issue | Auto-fixed via #2. Regression test `test_save_assessment_no_point_drift` confirms identical totals on round-trip. |
| "Cost Estimator missing from PDF" | ✅ Already fixed in Phase 7.3 — `_build_snapshot()` line 198 + `_cost.html` template render correctly | No-op |
| "Unified calculator engine" | ✅ Already done in Phase 7.2 — both `/sales/calculator/calculate` and `/sales/wizard/calculate-parallel` use the same `core.sales_calculator.calculate()` function | No-op |

**Files modified:**
- `frontend/src/pages/sales/components/ParallelSubclassPanel.jsx` — fixed field-name mapping (data.qualification, data.ielts_*, etc.) + added spouse block emission
- `frontend/src/pages/sales/steps/Step5Calculator.jsx` — removed marital_status gate; added `labelForBreakdown()` helper that maps `matched_key` to friendly labels

**New regression test (`tests/test_phase94_calculator_bugs.py`):**
1. `test_single_applicant_gets_10_partner_points` — confirms official AU rules
2. `test_batch_vs_parallel_same_total` — explicitly verifies the two endpoints return identical totals for same profile
3. `test_save_assessment_no_point_drift` — round-trip POST → fetch → POST yields same `best_total`
4. `test_parallel_returns_all_three_subclasses` — 189/190/491 all returned with best pick
5. `test_married_with_au_pr_spouse_gets_10` — AU PR spouse correctly maps to single_or_pr_partner

**Live UI screenshot confirmation:**
- Main calculator result: 90 pts (single, IELTS 7.5, bachelor, 6yrs OS exp)
- Parallel panel: 189 = 90 · 190 = 95 · 491 = 105 (all Eligible badges, 491 highlighted as best)
- Breakdown row: "No Migrating Partner Bonus +10" instead of confusing "Partner: 10"


### ⚡ Phase 9.3 — Hybrid LLM Model Router (Sonnet 4.6 + Haiku 4.5) (Jun 3, 2026)
**Status:** ✅ COMPLETE — 12/12 regression PASS · Live AI smoke-test passed on 3 occupations.

Sir's ask: "Hybrid: Sonnet for important + Haiku 4.5 for simple suggestions (cost saving ka best balance)".

**Root cause investigation (bonus fix):**
- User's Emergent Universal Key budget exceeded ($6.40 max hit).
- After top-up, error persisted because `/app/backend/.env` still had the OLD key.
- Updated `EMERGENT_LLM_KEY` to fresh key from `emergent_integrations_manager` → Sonnet calls instantly resumed.

**Hybrid Architecture (`/app/backend/core/ai_models.py` — NEW central registry):**

| Logical task | Model | Why |
|--------------|-------|-----|
| `occupation_suggester`  | **Haiku 4.5** | High-volume, simple JSON match · 4x cheaper · 2x faster |
| `step_document_helper`  | Haiku 4.5     | Simple hints (mapped in registry, not yet wired) |
| `ai_intelligence_quick` | Haiku 4.5     | Short helpers (mapped, not yet wired) |
| `resume_extractor`      | Sonnet 4.6    | Multi-section structured extraction · quality-critical |
| `proposal_standard`     | Sonnet 4.6    | Client-facing content · quality-critical |
| `country_guide`         | Sonnet 4.6    | Long-form authored content |
| `kb_ai_polish`          | Sonnet 4.6    | KB content polishing |
| `ai_verification`       | Sonnet 4.6    | Verification reasoning |
| `eligibility_reasoning` | Sonnet 4.6    | Mission-critical scoring AI |
| `ai_extract_admin`      | Sonnet 4.6    | High-stakes admin VETASSESS/state extraction |
| `proposal_premium`      | **Opus 4.6**  | Existing premium path (untouched) |

Centralized helper:
```python
from core.ai_models import model_for
CLAUDE_MODEL = model_for("occupation_suggester")  # → claude-haiku-4-5-20251001
```

**Files changed:**
- NEW: `/app/backend/core/ai_models.py` — central task → model registry
- MOD: `/app/backend/routers/sales_ai_helpers.py` — occupation suggester now uses `model_for("occupation_suggester")` → Haiku 4.5
- MOD: `/app/backend/.env` — `EMERGENT_LLM_KEY` refreshed to top-up'ed key

**Live AI smoke test (post-fix):**
| Input profile | Top-3 codes returned | Confidence |
|---------------|----------------------|------------|
| "CRM Manager, 15yr real estate" | 131112 Sales/Marketing Mgr · 132111 Corp GM · 225113 Marketing Specialist | HIGH/medium/medium |
| "Software Engineer at TCS, Java 5yr" | 261313 SW Engineer · 261312 Dev · 261311 Analyst Prog | HIGH/HIGH/medium |
| "Registered Nurse ICU, 8yr" | 254423 RN Critical Care · 254418 RN | HIGH/HIGH |

**Cost-savings estimate (Sonnet → Haiku for occupation suggester):**
- Input cost: $3 → $0.80 per 1M tokens (~73% cheaper)
- Output cost: $15 → $4 per 1M tokens (~73% cheaper)
- Avg prompt = ~8K tokens (large because we ship 892 AU codes) → ~$0.024 → $0.0064 per call (~73% saving)
- 1,000 sales sessions/month with 5 suggester calls each = $120/mo → **$32/mo** (saves $88/mo just on this one feature)

**Future tasks easily upgradable** — to switch any task between Sonnet/Haiku/Opus, just edit the `MODEL_FOR` dict in `core/ai_models.py`. No router code changes needed.


### 🧭 Phase 9.2 — Atlas Verify Card + Manual Tools UI (Jun 3, 2026)
**Status:** ✅ COMPLETE — Backend **12/12 PASS** (`tests/test_phase9_scrapers.py` extended). UI E2E verified via screenshots.

Sir's ask: "VETASSESS + State Nomination CSV upload UI banao + Sales wizard mein 'Verify in Atlas' button daalo".

**Two features shipped together:**

#### 1. Atlas Verify Card (Smart Sales Helper integration)
New sales-facing endpoint + UI component that surfaces Migration Atlas enrichment data inline during occupation selection.

**Backend** (`routers/anz_intel.py`):
- `GET /api/anz-intel/verify/{code}` — accessible to admin + case_manager + partner + all 4 sales roles
- Returns a compact, ready-to-render payload:
  - Title, ANZSCO code, classification dual-code, verification status
  - SkillSelect Tier 1-4 with friendly label + classification reason
  - Assessing authority (skill body) — name + URL
  - VETASSESS Group A-F + qualification/experience criteria
  - Full visa subclass eligibility array (189/190/491/482/186/187/485 etc)
  - State nomination matrix (NSW/VIC/QLD/SA/WA/TAS/NT/ACT) with 190 + 491 + demand level
- 400 on bad code · 404 on unknown · 403 on insufficient role · 200 on success

**Frontend** (`pages/sales/components/AtlasVerifyCard.jsx`):
- New compact teal-gradient card matching LEAMSS brand (no blue/indigo)
- SkillSelect Priority hero with tier-tone color coding (Tier 1/2 teal, Tier 3 gold, Tier 4 orange)
- Side-by-side Assessing Body + VETASSESS Group cards
- Visa eligibility pill grid with green ✓ / red ✗ markers per subclass
- State nomination table with 190/491 columns + demand badges (high/medium/low) + unit-group caveats
- Footer with "Download 4-Page Infosheet PDF" + "Open Atlas Dashboard" deep-links

**Frontend** (`pages/sales/steps/Step3Profile.jsx`):
- New "🗺️ Verify in Atlas" button placed inline on the Selected Occupation card
- Click toggles the AtlasVerifyCard drawer below
- Auto-collapses on "Change" so sales can swap occupations cleanly

**Verified live for code 261313 (Software Engineer)**:
- Tier 4 · Other Eligible (STSOL/ROL) — correct (legacy migrated record, not in CSOL)
- ACS · Australian Computer Society
- Visas eligible: 189, 190, 491, 482, 186 (greens) · 187, 485 (reds)
- States: NSW (190+491, high), VIC (190+491, high), QLD (190+491, high), WA (190+491, medium)

#### 2. Manual Tools UI (Admin Audit Dashboard)
New "Step 5 — Manual Tools (CSV + AI Extract)" tab on the Migration Atlas Audit Dashboard to extend Atlas data for states/sources that don't scrape (VIC, SA, ACT, NT, TAS, WA).

**Frontend** (`pages/admin/AnzIntelAudit.jsx`):
- New `ManualToolsTab` rendering two cards side-by-side:
  - **Bulk CSV Upload Card**: Download template → upload CSV → preview (rows / valid / matched / unmatched) → optional "overwrite verified" toggle → commit
  - **AI Paste-Extract Card**: 6-digit code input + intent selector (vetassess_group | acs_rules | state_nomination) + raw-text textarea (paste from official site) → AI preview shows extracted JSON → commit
- Powered by pre-existing backend endpoints `/api/anz-intel/bulk-upload-csv/{preview,commit,template}` and `/ai-extract/{preview,commit}` (Claude Sonnet 4.6 via Emergent LLM Key)

**Tests added (`tests/test_phase9_scrapers.py`):**
- 5 new tests covering verify endpoint: partner-can-read, bad-code-400, unknown-code-404, unauthenticated-blocked, Tier 1 classification correctness
- Combined with 7 existing → 12/12 PASS in 4.67s


### 🗺️ Phase 9.1 — Migration Atlas Scrapers Expansion (Jun 3, 2026)
**Status:** ✅ COMPLETE — Backend **7/7 PASS** (`tests/test_phase9_scrapers.py`). UI verified via screenshots.

Sir's ask: "Migration Atlas ko complete karo — VETASSESS, State Nomination, SkillSelect scrapers banao, official sources only."

**3 new scrapers shipped (`/app/backend/core/scrapers/`):**

1. **State Nominations Scraper** (`state_nominations.py`)
   - **NSW** (https://www.nsw.gov.au/visas-and-migration/skilled-visas/nsw-skills-lists): scrapes 2 HTML tables → 87 4-digit ANZSCO unit groups for 190 + 491 nomination eligibility, then expands to all 6-digit children in occupation_master (238 records updated)
   - **QLD** (https://migration.qld.gov.au/.../offshore-queensland-skilled-occupation-lists-(qsol)): direct 6-digit ANZSCO match with 190/491 columns + caveats (97 records updated)
   - **WA** (https://migration.wa.gov.au/.../state-nominated-migration-program): page is JS-driven → 0 records on initial scrape (graceful failure). Documented as "use CSV upload" for now.
   - VIC, ACT, NT, SA, TAS publicly not scrapable (JS-driven or rule-based) — admins should use CSV Upload / AI-Extract tools

2. **SkillSelect 4-Tier Classifier** (`skillselect_tiers.py`)
   - **DETERMINISTIC** — uses existing `pathway_list` data from Home Affairs scrape (CSOL/MLTSSL/STSOL/ROL) + ANZSCO Major Group rules
   - **No network calls** — fully offline classifier
   - Tier mapping (per Home Affairs 2025-26 SkillSelect framework):
     - Tier 1: Health + Education priority occupations (ANZSCO 25xx, 24xx with CSOL/MLTSSL)
     - Tier 2: CSOL members (Core Skills Occupation List)
     - Tier 3: MLTSSL-only / critical regional trades (33xx, 34xx with 491 eligibility)
     - Tier 4: STSOL/ROL only / fallback
   - Distribution across 892 AU codes: **Tier 1 = 94, Tier 2 = 276, Tier 3 = 15, Tier 4 = 507**
   - Idempotent (`skipped_already_set` on re-run)

3. **VETASSESS Group A-F Static Seed** (`vetassess_groups.py`)
   - vetassess.com.au is JS-driven — bulk download not available
   - Curated, audited static seed of 142 top-occupation → Group A/B/C/D/E/F mappings (per VETASSESS published criteria)
   - Distribution: A=23, B=31, C=31, D=3, E=24, F=3
   - Includes auto-populated `qualification_required`, `experience_required`, `pre_qual_experience_allowed` per group
   - Extensible via existing CSV Upload + AI-Extract tools

**API endpoints added (`routers/anz_intel.py`):**
- `POST /api/anz-intel/scrapers/state-nominations/run?dry_run=`
- `POST /api/anz-intel/scrapers/skillselect-tiers/run?dry_run=`
- `POST /api/anz-intel/scrapers/vetassess-groups/run?dry_run=`
- `GET /api/anz-intel/scrapers/list` updated to return all 4 ready scrapers (was only home_affairs ready before)

**Frontend (`pages/admin/AnzIntelAudit.jsx`):**
- ScrapersTab fully rewritten to support multiple scrapers
- Each scraper card has its own Dry-Run button + per-scraper preview cards + Commit button
- New `ScraperDryRunPreview` component renders scraper-specific stats (HA: fetched/updated counts; State: NSW/QLD counts; SkillSelect: 4 tier counts; VETASSESS: 6 group counts)
- After commit, parent `fetchAll()` auto-refreshes hero stats + field coverage bars

**Field Coverage Audit Dashboard (after all 4 scrapers committed):**
| Field                        | Before (Phase 9) | After (Phase 9.1) |
|------------------------------|------------------|---------------------|
| Salary & Workforce           | 93.5%            | 93.5%               |
| Job Tasks                    | 94.1%            | 94.1%               |
| Top Industries               | 93.5%            | 93.5%               |
| State % Distribution         | 93.5%            | 93.5%               |
| Skill Body                   | 62.0%            | 62.0%               |
| **Skill Body Criteria (VETASSESS Group)** | 0%   | **14.7%** ⬆        |
| Visa Eligibility             | 63.7%            | 63.7%               |
| **State Nomination**         | 4.1%             | **27.3%** ⬆⬆       |
| **SkillSelect Tier**         | 0%               | **95.3%** ⬆⬆⬆     |
| ANZSCO v1.3 ↔ v2022          | 63.3%            | 63.3%               |

**Tests:** `tests/test_phase9_scrapers.py` (7 cases): scrapers list, SkillSelect dry-run + idempotency, VETASSESS dry-run, State nominations live scrape (skippable via `SKIP_NETWORK_TESTS=1`), audit-summary includes new fields, RBAC blocks partner.


### ⚡ Phase 7.5 — Pipeline Cockpit Full Wiring (May 25, 2026)
**Status:** ✅ COMPLETE · **Testing**: 13/13 backend pytest + frontend E2E 100% (testing agent iterations 113, 114) · **Zero blue/indigo violations** · **Sanity route-mismatch issue FIXED**.

Sir's ask: "Static cockpit mockup ko production me convert karo — live data, AI brief, drill-in, Cmd-K. NO blue/indigo."

**Backend (`routers/cockpit.py`)** — 4 new endpoints under `/api/cockpit`:
- `GET /funnel` — live counts across 6 stages aggregated from `leads` + `sales_assessments` + `pre_assessments` (returns leads/assessments/pa/proposals/cases/closed + total_active)
- `GET /cards?stage&owner&search&sort&limit` — unified normalized card list. Maps PA stage groups: PA = new/payment_pending/payment_received/documents_submitted/under_review/approved/express_pending_approval, Proposals = proposal_sent, Cases = proposal_paid/awaiting_final_approval/case_created, Closed = rejected/refunded/express_rejected
- `GET /brief` — AI insights for sidebar (stale leads 48h cutoff, payment-pending PAs, proposals awaiting decision, KB items pending verification)
- `GET /card/{lead|assessment|pa}/{id}` — drill-in detail with deep-link to source page

**RBAC scoping:**
- Admin/case_manager/admin_owner → all records
- Sales/partner roles → records they created/own (uses `created_by` for assessments, `partner_id` for PAs, `assigned_to` for leads)

**Stage → Lifecycle index mapping** (`LIFECYCLE_FROM_PA_STAGE`) → renders 7-step progress bar in card UI (0=Created → 6=Case Created)

**Frontend (`pages/admin/Cockpit.jsx`)** — Production cockpit replacing the deprecated mockup:
- Route: `/admin/cockpit` (RBAC: admin_owner/admin/sales_*/case_manager/partner)
- Deprecated mockup retained at `/admin/cockpit-mockup` per "hide-not-delete" rule
- Auto-refresh: silent 30s polling (funnel + cards). Manual refresh button with spin animation.
- Layout: Left sidebar (LEAMSS branded with nav menu) · Main (topbar + 6 funnel chips + filter row + 3-col card grid) · Right AI Co-Pilot sidebar (Quick Commands, 5 Quick Action buttons, Today's AI Brief live from `/brief`)
- Cmd-K modal (Ctrl/Cmd+K shortcut) — functional with Quick Actions list + inline card name search
- Pipeline cards: name + countries + score badge (gold for scored, slate "New" for leads) + ID + 7-step lifecycle bar (teal=done, orange=current, gray=pending, pulse animation on current) + owner avatar/timestamp + urgency pill (high=red/medium=orange/low=teal) + next-action CTA
- Drill-in Sheet drawer: 7-step lifecycle timeline (teal checks/gold-bordered current/gray pending) + Next Action banner (teal-wash background) + Open Full View (teal) + WhatsApp buttons

**LEAMSS Brand Compliance — ZERO BLUE/INDIGO:**
- Teal `#0F766E` primary (was #2563EB blue) — sidebar nav active, CTA buttons, "+ New Client", drill-in "Open Full View"
- Warm Orange `#EA7C2E` (was indigo) — current-step pulse, medium urgency pill, lifecycle bar current segment
- Brand Red `#D32F2F` — high urgency pill ring
- Gold `#D4A017` — score badge, sidebar AI Brief icons
- Charcoal/Cream/Slate neutrals only

**Live Data Snapshot (verified):**
- Funnel: Leads 21 · Assessments 3 · Pre-Assessments 83 · Proposals 5 · Active Cases 9 · Closed 0 · Total 121 active records
- AI Brief: 21 stale leads, 5 proposals awaiting decision, 3 KB items pending verification

**Tests:** `tests/test_iteration132_phase_75_cockpit.py` (10 cases: funnel/cards default/filter/search/sort/brief/RBAC/drill-in not-found/drill-in bad-kind/unauthenticated 401) + `tests/test_iteration114_cockpit_routes.py` (3 cases: brief cta_links validation + PA/assessment deep_link values)

**Sanity Fix (iteration_114) — Route Mismatch Eliminated:**
- **Root cause:** Iteration_113 testing flagged that `/admin/pre-assessments`, `/admin/verification-hub`, `/admin/leads`, `/admin/cases`, `/sales/assessments` redirected to Login during regression. These URLs do NOT exist in `App.js` — they were internal AdminDashboard tab names OR had different paths (e.g., `/admin/verify-hub`, `/sales/my-assessments`).
- **Fix:**
  1. `AdminDashboard.jsx` now reads `?tab=…` from URL via `useSearchParams` + syncs `activeTab` on mount and URL change → enables deep-linking to internal tabs
  2. `Cockpit.jsx` left-sidebar nav, AI Quick Actions, Cmd-K Quick Actions all updated to real routes: `/admin?tab=pre-assessments`, `/admin?tab=cases`, `/admin/verify-hub`, `/sales/my-assessments`, `/sales/client-assessment`, `/admin/kb/occupation-master`
  3. Removed "Leads" sidebar item (no standalone Leads page yet — folded into PA management), added "Smart Sales Helper" entry
  4. `routers/cockpit.py` brief endpoint `cta_link` + card detail `deep_link` updated to same pattern
- **Verification:** 13/13 backend pytest + 16/16 frontend nav-target E2E (testing agent iteration_114) — every cockpit click lands on a real rendered page.

### 🎨 Phase 8 — Premium PDF Renderer v2 (HTML→PDF · WeasyPrint) (May 25, 2026)
**Status:** ✅ COMPLETE — Backend **7/7 new + 51/51 full regression PASS** (`tests/test_iteration131_phase_8_pdf_v2.py`). All 3 tiers (teaser/full/proposal) render successfully via API.

Sir's ask: "Premium PDF design upgrade — naya unique LEAMSS-branded design, koi blue/indigo nahi chahiye."

**Brand palette (extracted from LEAMSS logo via AI analysis):**
- Teal `#0F766E` (primary, from "LEA" + "MS" in logo)
- Warm Orange `#EA7C2E` (accent, from "M" letter)
- Brand Red `#D32F2F` (highlight, from "S" letter)
- Gold `#D4A017` (premium seal / certificate accent)
- Charcoal `#1F2937`, Cream `#FAFAF9`, Slate `#64748B`
- **Zero blue/indigo** anywhere.

**Tech stack additions:**
- `weasyprint==68.1` + `pydyf==0.12.1` + `tinycss2`, `cssselect2`, `pyphen`, `fonttools` — pure-Python HTML→PDF
- `Playfair Display` (variable font) downloaded to `/app/backend/fonts/` for premium serif headings
- Existing `Manrope` retained for body / sans-serif

**Architecture:**
- New package: `/app/backend/core/report_v2/`
  - `renderer.py` — public `render_pdf_v2(snapshot) -> bytes`
  - `css/theme.css` — single LEAMSS-branded stylesheet (page setup, brand variables, typography, cards, pills, charts)
  - `templates/` (Jinja2):
    - `base.html` — master skeleton with tier-aware `{% include %}` switching
    - `_cover.html`, `_executive.html`, `_client_profile.html`
    - `_anzsco.html` (compact stat tiles + state bars + industries + tasks columns)
    - `_country.html` (per-country hero with teal/red/lime gradient + occupation + visa + state demand + points bars)
    - `_process.html` (12-step ownership cards)
    - `_cost.html` (category-grouped magazine-style cost cards + teal-gold "Total Investment" hero)
    - `_country_guide.html` (verified KB content with FAQ cards)
    - `_checklist.html` (premium 7-category grid)
    - `_protection.html` (gold-bordered certificate card with covered/excluded two-column)
    - `_disclaimer.html`, `_contact.html` (final thank-you with "We Value Emotions" hero)

**Router wiring (`routers/assessment_reports.py`):**
- `USE_REPORT_V2=true` env flag (default true) — set `false` to fall back to legacy ReportLab engine
- `from core.report_v2 import render_pdf_v2` aliased to `render_pdf`, drop-in replacement
- Zero changes to API contract — `/api/assessment-reports/{id}/pdf?tier=` works identically

**Tier-based gating (preserved from Phase 7.3):**
- **Teaser** (7 pages, ~225 KB) — Cover · Exec Summary · Profile · Process · Protection · Disclaimer · Contact
- **Full** (15 pages, ~298 KB) — Teaser + ANZSCO Deep-Dive + Per-Country + Cost + Country Guide + Checklist
- **Proposal** (15 pages, ~298 KB) — Full + future proposal-letter cover

**Visual proof (real generated PDF · client "Phase 7.3 Demo Sir" · AU 80 pts):**
- Page 1 Cover: dark-teal gradient with orbital ring, white logo card, Playfair "Assessment Report" title, gold italic subtitle "— Your migration journey, mapped.", glass-effect client card with name/pathway/score/generated/tier, gold "80 POINTS" donut, branded footer (95% AI-vision premium rating)
- Page 2 Executive: "Top Recommendation" card with teal-left-rule + score 80 + green ELIGIBLE pill, full comparison table, 12-step horizontal journey strip with active orange "01 Assessment · You are here" (98% rating)
- Page 4 ANZSCO Deep-Dive: 3 stat tiles (AUD 2,537 / 203,200 / 38), state bars (NSW 36.2%, VIC 35.6%…), industries 2-col grid, tasks 2-col (95% rating)
- Page 5 Country AU: full teal gradient hero with "Section 04.1 · Australia · Pathway: Visa 189 · 80 / pass mark 65 · ✓ ELIGIBLE" white pill
- Page 9 Cost: teal-gold "Total Investment · INR 697,000" hero card with "Protected by LEAMSS Protection Policy" note
- Page 13 Protection: gold-bordered "100% Refund Guarantee" certificate, "VERIFIED POLICY · V1.0" badge, teal-checks Covered / red-X Not Covered two-column, 3 stat tiles
- Page 15 Contact: centered logo, "We Value Emotions" in italic Playfair, teal contact card

**Page-break safeguards:**
- `orphans: 4; widows: 4;` on body
- `break-inside: avoid` on cards, tables, headers, notes
- `break-after: avoid` on headings and last-child of `.page`
- Content trimming: tasks 8, industries 4, FAQs 5 (eliminated all single-line orphan pages — 17 → 15 pages)

**Acceptance results:**
- ✅ AI vision: 95-98% premium quality rating across all 6 key pages
- ✅ 7/7 new pytest suite (full/teaser/proposal tiers + no-optional-blocks + immutability)
- ✅ 51/51 full Phase 6-7 regression — zero impact on assessment-reports endpoints
- ✅ Generation time: ~1.2s per report (acceptable)
- ✅ End-to-end through API: `POST /generate → GET {id}/pdf?tier=full` works for all 3 tiers

### 🔄 Phase 7.3.5 — Tier Auto-Advance Hook + Client Notification (May 25, 2026)
**Status:** ✅ COMPLETE — **3/3 helper tests PASS · 51/51 full regression PASS**.

Sir-approved smart enhancement: tier auto-flips + client gets a "🎉 Full report unlocked" notification.

**Implementation (`core/report_tier_hook.py`):**
- Idempotent helper `auto_upgrade_report_tiers_for_pa(pa_id, new_stage, payment_ref)`
- Stage → Tier mapping: `proposal_paid` / `awaiting_final_approval` → `full` · `case_created` → `proposal`
- **Tier never downgrades** — once at proposal, stays proposal even if PA reverses
- Each upgrade audit-logged with `tier_upgraded_by="auto:pa_stage_hook"`, payment ref, trigger stage, and old tier
- **NEW:** After every successful tier upgrade, automatically creates a `notifications` collection entry:
  - In-app notification with friendly Hinglish title/message
  - WhatsApp template ready-to-send (in `meta.wa_template`) — pre-filled with client name + share link
  - Distinct templates for `full` ("🎉 Full Assessment Report Unlocked") and `proposal` ("🛡️ Case Active") tiers

**Hooks installed:**
- `pre_assess_portal.py` proposal_paid path: upgrade to full + notify
- `pre_assess_portal.py` case_created path: upgrade to proposal + notify

### 🧹 Phase 7.4 — Profile Merge (May 25, 2026)
**Status:** ✅ PART 1 COMPLETE — Hide-not-delete enforced.

Sir's directive: "Delete → Hide". Pure UX consolidation, zero data loss, routes stay live for direct URL access.

**Frontend changes:**
- `pages/AdminDashboard.jsx` — Sales menu cleaned. Commented out (not deleted) two menu items:
  - `Client Profiles` → /eligibility/profiles
  - `New Profile` → /eligibility/new-assessment
  → Comments preserved for easy re-enable; backend routes + pages untouched (Sir's "hide" rule)
- `steps/Step1Start.jsx` — NEW "Save time — let the client self-fill" emerald CTA card:
  - Generates secure Info Sheet link via existing `/api/eligibility/info-sheet/generate-link`
  - Copy / Open / WhatsApp (deep-link prefilled with client name + LEAMSS branded message)
  - Validity badge (30 days default) — once client submits, Step 3 auto-populates

**Outcome for Sir's complaint:**
- "3 wizards confusing" → Admin/Partner menus no longer show parallel "New Profile" flows
- "Send Infosheet alag hai" → Info Sheet send is now ONE-CLICK inside the unified Client Assessment Wizard
- Zero deletions, fully reversible via uncommenting menu lines

### 📄 Phase 7.3 — Report KB Data Injection + 3-Tier Gating (May 25, 2026)
**Status:** ✅ COMPLETE — Backend **8/8 PASS · 48/48 full regression PASS** (`tests/test_iteration129_phase_73.py`). PDF visual verified via AI vision on 3 grids.

Sir's complaints addressed in this phase:
- ❌ "Tasks blank in PDF" → ✅ ANZSCO Deep-Dive section with tasks from Feb 2026 Excel
- ❌ "Fees mein amounts nahi hain" → ✅ Cost & Investment Breakdown with itemized amounts + total
- ❌ "Protection Policy nahi dikh raha" → ✅ Dedicated Section 7 with covered/excluded refund terms
- ❌ "Heavy redesign baad mein" → ✅ Existing PDF layout retained, ONLY KB data injected

**Backend additions** (`/app/backend/core/report_renderer.py`):
- `_section_anzsco_profile()` — Renders ANZSCO 4-digit deep-dive (median earnings AUD, employed count, demographics, state distribution top 6, top 5 industries, tasks list, education profile). Sourced from `anzsco_4digit_master` (1,236 codes from Feb 2026 ABS).
- `_section_cost_estimator()` — Renders Cost & Investment table grouped by category (Government Fees, Skill Assessment, English Test, LEAMSS Professional Fees, Protection Policy Coverage), with itemized amounts and currency-grouped totals. Includes validity notes.
- `_section_protection_policy()` — Renders LEAMSS USP page with title, description (markdown stripped), "What is Covered" list, "What is NOT Covered" list, claim window days, applicable countries.

**Snapshot builder** (`_build_snapshot` in `routers/assessment_reports.py`):
- Now fetches `anzsco_4digit_master` using 4-digit parent of occupation.code
- Now fetches `cost_estimator` from the assessment doc
- Now fetches default LEAMSS `protection_policies` (verified) — or any verified policy as fallback
- All injected into snapshot data (immutable, integrity-hashed)

**3-Tier PDF Gating** (Sir's directive: internal logic, no Stripe):
- `GET /api/assessment-reports/{snapshot_id}/pdf?tier={teaser|full|proposal}` — RBAC-aware
- `POST /api/assessment-reports/{snapshot_id}/upgrade-tier` — admin or owner flips tier (internal payment marker, no Stripe)
- Public PDF endpoint (`/public/{share_token}/pdf`) reads stored `render_tier` (defaults to teaser)
- Teaser tier: Cover + Executive Summary + Client Profile + Process/Cost + **Protection Policy** + Disclaimer (~7 pages)
- Full tier: + ANZSCO Deep-Dive + Per-Country Details + Cost & Investment Breakdown + Country Guide + Document Checklist (~15 pages)
- Proposal tier: identical to full + (future) proposal letter cover

**Visual proof** (3 AI-vision checks done on real generated PDFs):
- Page 4: ANZSCO 2613 Software & Apps Programmers · AUD 2,537 weekly · NSW 36% · top industry Professional Services · tasks list rendered
- Page 9: Cost & Investment Breakdown · INR 430,000 visa + INR 50,000 ACS + INR 22,000 IELTS + INR 195,000 LEAMSS = **INR 697,000 total** · "Protected by LEAMSS Protection Policy" note
- Page 13: SECTION 7 — LEAMSS PROTECTION POLICY · "100% Refund Guarantee" · Covers Professional/Government/Body Fees · Excludes English/Medical/PCC · 90-day claim window · AU/CA/NZ/UK/USA applicable

**File counts:**
- Full tier PDF: 15 pages (~31 KB)
- Teaser tier PDF: 7 pages (~13 KB)

### 🧮 Phase 7.2 — Unified Wizard + Cost Estimator (May 25, 2026)
**Status:** ✅ COMPLETE — Backend **8/8 PASS · 40/40 full regression PASS**. UI verified (8-step wizard with Cost Estimator + Parallel Subclass Comparison + ANZSCO Auto-populate).

Sir's pivot: instead of building a parallel V2 wizard, **enhance the existing Smart Sales Helper** (no compromise on quality, no parallel code paths).

**Backend additions** (`/api/sales/wizard/...`):
- `POST /calculate-parallel` — Multi-subclass parallel calc engine. Single function used by both wizard and calculator (Sir's "1 engine, not 2" demand). Returns per-subclass `{total, breakdown, eligible}` + `best_subclass`.
- `GET /cost-estimator/defaults` — KB-driven defaults: Government Fees (country_template.fees), Skill Assessment (skill_body_master), English Test placeholder, LEAMSS Professional Fees, Protection Policy Coverage (auto-includes verified LEAMSS USP).
- `POST /cost-estimator/save` — Persists to `sales_assessments.cost_estimator` with currency-grouped totals.
- `GET /cost-estimator/{assessment_id}` — RBAC-gated retrieve.

**Frontend changes**:
- `lib/constants.js` — STEPS extended from 7 → 8 (added "Cost Estimator" between Calculator and Review, new `Coins` icon)
- `steps/Step6CostEstimator.jsx` — NEW step. Auto-loads KB defaults on first visit, inline editable line items (category/label/amount/currency/notes), KB source attribution badge, currency-grouped totals card with Protection Policy reminder.
- `components/ParallelSubclassPanel.jsx` — NEW. Below Live Calculation in Step 5. Calls `/calculate-parallel` for all subclasses per active country (AU: 189/190/491, CA: EE, NZ: SMC, UK: Skilled, USA: H1B + EB2-NIW). Highlights best subclass with gold border + ⭐ "Best: Subclass X" badge.
- `components/ANZSCOPreviewCard.jsx` — NEW. After occupation selection in Step 3, fetches `/api/kb-unified/anzsco/{4digit}` and renders compact card with: median weekly earnings (AUD), employed count, median age, female share %, top 4 states, top 3 industries, education distribution badges, expandable Tasks list (8+). Data source attribution.
- `ClientAssessment.jsx` — Wired Step 6 between Calculator (5) and Review (now 7). Save now lands at Step 8 (Done). `headers` passed to Step 5.

**Visual proof** (multiple screenshots):
- 8-step horizontal nav working correctly
- Step 3: Selected Occupation card + ANZSCO preview card with ABS Feb 2026 attribution
- Step 5: Live Calculation (existing) + **Parallel Subclass Comparison panel** showing 189/190/491 side-by-side with eligible badges and best-subclass highlight
- Step 6: Cost Estimator with auto-loaded KB defaults, currency totals, Protection Policy coverage row

**Known polish item:** Parallel calc may differ slightly from in-wizard Live Calc when "Additional Factors" toggles are active — Live Calc applies extra bonuses via a wrapper. Future iteration will sync both engines fully.

**Pending (deferred to Phase 7.4 — Profile Merge):**
- Hide NEW Profiles tab + Client Profile sub-tabs (deferred)

### 🏗️ Phase 7.1 — KB Unification FOUNDATION (May 25, 2026)

### 🏗️ Phase 7.1 — KB Unification FOUNDATION (May 25, 2026)
**Status:** ✅ COMPLETE — Backend **12/12 PASS · 33/33 full regression PASS** (`tests/test_iteration127_phase_71.py`). UI E2E verified via screenshots (Verification Hub + Protection Policies admin).

Sir requested 3-part Phase 7: JODNA (connect) → WIZARD → REPORT. Part 1 (JODNA) shipped with strict constraints:
- "Delete" → "Hide" (status field added everywhere — zero data loss)
- No Stripe integration (internal logic only)
- No Cockpit work (deferred)
- No heavy design overhaul (current PDF layout retained)
- Admin-controlled points (no runtime override)
- Phase-level verification checkpoint before Part 2

**Backend additions:**
- `core/anzsco_excel_importer.py` — Parses Sir's Feb 2026 ABS Excel (9 sheets) into `anzsco_4digit_master`. Idempotent upserts. Imported **1,236 occupations** in 1.17s with full profiles (tasks, weekly earnings, industries, state distribution, age, education).
- `routers/protection_policies.py` — LEAMSS USP managed entity. Full CRUD + verify (mandatory source URL) + hide/unhide (Sir's directive: no delete). Default LEAMSS policy seeded.
- `routers/kb_unified.py` — `/import-anzsco-excel` upload endpoint + `/import-anzsco-default` one-click + `/verification-hub` 4-entity aggregator + `/anzsco/{code}` + `/occupation-full/{code}` (joined view).
- `migrations/phase71_kb_unification.py` — Idempotent: UK + USA templates seeded (Sir's gap fix), default LEAMSS Protection Policy seeded, 129 existing occupations backfilled with `custom_qa=[]` and `status=active`.

**Frontend additions:**
- `pages/admin/VerificationHub.jsx` — Single dashboard. ANZSCO master card (1,236 codes loaded · ABS Feb 2026), 4 stat tiles (Occupations · Country Templates · Country Guides · Protection Policies), 4 tabs with pending lists, one-click Re-import Excel button.
- `pages/admin/ProtectionPoliciesAdmin.jsx` — 3-panel editor (mirrors Country Guides UX): left rail, full editor with Covers/Excludes/Claim Days, Verify with source URL, Hide/Unhide.
- KB Admin home: 4 quick-launch buttons (Verification Hub, Occupation Master, Country Guides, Protection Policies).

**Verified outcomes:**
- Sample 4-digit profile: 2613 (Software Programmers) → AUD 2,537/week median, 38 median age, NSW 36% + VIC 36%, 56% bachelor + 27% post-grad, top industry Professional Services. **All from ABS official source.**
- Verification Hub aggregate: Occupations 1.6% verified, Country Templates 16.7%, Country Guides 40%, Protection Policies 0% (default policy needs Sir's verification).
- 5 country_templates now present (AU verified, CA/NZ/UK/USA draft).

### 🚀 Phase 6.10 Part 3 — Unified Workflow + Checklist Gating + Country Guides (May 24, 2026)
**Status:** ✅ COMPLETE — Backend **21/21 PASS** (`tests/test_iteration125_phase_6102.py` + `tests/test_iteration126_phase_6103.py`). UI E2E verified via screenshots (Step 7 tracker + locked checklist + public country page).

**🐛 Bug Fix (May 24, 2026 evening):** Sir reported "verified Country Guide AU but content not in Assessment Report PDF". Root cause: `_build_snapshot()` in `assessment_reports.py` never queried the `country_guides` collection, so the renderer's `snap.get("country_guides")` was always empty and Section 5 fell back to a stub.

Fix shipped:
- `_build_snapshot()` now fetches each target country's verified `country_guides` doc + visa_subclasses meta from `country_templates`.
- `_section_country_guide()` rewritten to render Hero subtitle + all non-empty sections (markdown body) + FAQ pairs.
- `_section_country()` visa table now falls back to `country_templates.visa_subclasses[]` meta for the Notes column when occupation-level notes are blank.
- Verified via AI vision scan of generated page 7: full content (Country Overview, PR Pathways, Eligibility, Fees, Timeline, Pros/Cons, Settlement, 4 FAQs) now appears in PDF.

Sir requested the full 3-section delivery in a single shot.

**A) Unified Workflow Status Tracker (P0)**
- New endpoint `GET /api/sales/assessments/{id}/lifecycle` returning 7-step journey:
  `created → calculated → report_generated → pa_created → pa_fee_paid → main_fee_paid → case_created`
- Each step carries `{completed, timestamp, actor, detail, link}` for one-click navigation.
- PA stage → lifecycle index mapping (`_PA_STAGE_TO_LIFECYCLE_INDEX`) keeps the rule deterministic.
- Step 7 of the wizard renders a vertical timeline card with progress pill (`Client Journey · 17% complete · Step 2/7`).

**B) Detailed Checklist Gating (P0)**
- `GET /api/sales/assessments/{id}/checklist` now gates detail behind **Main Service Fee Paid** state.
- Unlock stages: `proposal_paid / awaiting_final_approval / case_created`.
- Pre-payment response carries `is_locked=true`, `unlock_reason`, plus full `stats` (so the indicative count is still visible).
- Frontend renders an amber "🔒 Detailed Checklist Locked" card with reason + what's visible / what unlocks.

**C) Admin Country Guides + Public Pages (P1)**
- New collection `country_guides` (one document per country: AU/CA/NZ/UK/USA pre-seeded as drafts).
- New router `/api/country-guides/...` (11 endpoints): list / detail / CRUD / verify / AI-draft / public-list / public-detail.
- `POST /{code}/ai-draft` calls Claude Sonnet 4.6 (`core/kb_ai.py` pattern) — generates `{hero_subtitle, sections{}, faq[], admin_verify_note}` cached on the doc's `ai_draft` block. Admin reviews + copy-to-editor.
- Every edit auto-reverts status to `draft` — admin must `POST /{code}/verify` with a mandatory `source_reference` URL to publish.
- Public endpoints `/public` and `/public/{code}` only return `verified` guides (404 on drafts/archived).
- New admin page `/admin/country-guides` — 2-column layout: left rail (5 country list with status pills) + right editor (Hero / Sections (7) / FAQ / AI Draft tabs).
- New public pages `/countries` (verified-only grid) and `/countries/:code` (branded read-only with Hero CTA + sections + collapsible FAQ + contact block).
- Entry-point: violet "Country Guides" button on Eligibility Knowledge Base admin home.

**Files Added (4):**
- Backend: `routers/country_guides.py`, `tests/test_iteration126_phase_6103.py`
- Frontend: `pages/admin/CountryGuidesAdmin.jsx`, `pages/PublicCountryGuide.jsx`, `pages/PublicCountryIndex.jsx`

**Files Modified (4):**
- Backend: `routers/sales_assessments.py` (gated checklist + new lifecycle endpoint), `server.py` (router registration)
- Frontend: `pages/sales/steps/Step7Done.jsx` (Client Journey tracker + locked-checklist UI), `App.js` (3 new routes), `pages/admin/EligibilityKnowledgeBase.jsx` (Country Guides entry button)

### 📄 Phase 6.10 Part 2 — Professional Report Engine (May 24, 2026)
**Status:** ✅ COMPLETE — Backend **10/10 PASS** (`tests/test_iteration125_phase_6102.py`) · UI E2E verified (public share view + branded PDF inspected).

Sir uploaded LEAMSS branding artifacts (counseling sheet + sample assessment report). Built end-to-end immutable, branded report pipeline matching electric blue + deep indigo + gold accent palette.

**Backend** (`/api/assessment-reports/...`):
- `POST /generate` — Builds frozen snapshot from assessment + Knowledge Base. Records `data_integrity_hash` (SHA-256). Surfaces warnings when KB template/occupation is still `draft`.
- `GET /` — Lists user's reports (admin sees all, owner sees own). Sorted recent-first.
- `GET /{snapshot_id}` & `GET /{snapshot_id}/pdf` — RBAC-gated metadata + branded PDF stream.
- `POST /{snapshot_id}/share` (1/7/30/90 days), `DELETE /{snapshot_id}/share` (revoke). 410 returned on revoked tokens.
- `GET /public/{share_token}` + `/public/{share_token}/pdf` — no-auth viewer for client.
- `POST /{snapshot_id}/email` — **MOCKED** (needs `RESEND_API_KEY` for live dispatch).
- Snapshot is immutable: PUT/PATCH return 404/405.

**PDF Renderer (`core/report_renderer.py`)** — ReportLab A4, branded sections: Cover · Executive Summary · Client Profile · Per-Country Details (AU/CA/NZ) · Points Breakdown · Visa Pathways · State/Territory Demand · Disclaimer · Footer with snapshot ID + integrity hash.

**Frontend:**
- `Step7Done.jsx` — Added `ReportActions` widget (amber "Generate Report" → "Public Link" toggle + modal with Copy/Open/WhatsApp).
- New `PublicReportView.jsx` route `/reports/view/:token` — branded preview with Download PDF button, tamper-evident hash badge, contact details.

**Verification Results (May 24, 2026):**
- 10/10 backend pytest PASS
- Live curl: PDF = 19 KB, 11 pages, `%PDF-1.4` magic confirmed
- AI vision scan of generated PDF confirms: electric blue + deep indigo + gold branding, professional immigration-consultancy layout, all sections rendered correctly
- Public Share View renders with LEAMSS header, snapshot ID, Top Recommendation (🇨🇦 Canada 372), integrity hash, contact card

### 🗂️ Phase 6.9.2 / 6.9.3 / 6.9.4 / 6.9.5 — Verified Knowledge Base Stack (May 22-23, 2026)
**Status:** ✅ COMPLETE — Backend **41/41 new PASS · 75/76 full regression (1 network blip)** · UI E2E verified for all 4 tabs + 3-panel editor.

Sir requested all 4 sub-modules together (no sequential STOP). Built in parallel:

**6.9.2 — ANZSCO / NOC Bulk Import**
- Two-step preview→commit flow at `POST /api/occupation-master/import/preview` and `/commit`
- Auto-detects column mappings (code/title/skill_level/unit_group/tasks/alt_titles) with fuzzy keyword matching
- Detects duplicates in-file + in-DB before commit, shows admin warning
- `on_duplicate=skip|update` strategies; update preserves verification + linked_product_id + assessing_authority + visa_pathways + state_territory_eligibility
- All imported rows land as `draft`; admin verifies later

**6.9.3 — AI Draft + Admin Verify (3-panel editor)**
- New helper `core/kb_ai.py` — single integration point for Claude Sonnet 4.6 via Emergent LLM Key
- `POST /api/occupation-master/{id}/ai-draft` — generates `{description, typical_tasks, qualification_rules, ai_confidence_note}`, caches on the doc's `ai_draft` block; strict prompt forbids inventing fees/deadlines
- `POST /api/skill-body-master/{id}/ai-draft` — same workflow for assessing bodies
- `POST /api/kb/polish-text` — "✨ Polish with AI" preserves facts/numbers/names, improves grammar+tone
- `POST /api/occupation-master/{id}/verify` — admin marks `verified` with mandatory `source_reference`
- Frontend: 3-panel editor (`AI Draft / Admin Edit / Official Source`) with Polish button on description + typical_tasks, mandatory source URL before Verify

**6.9.4 — Status System + Settings**
- New `kb_settings` collection with `outdated_threshold_months` (default 6), `verification_gate_percent` (default 90), `enforce_verified_only` (default false)
- `GET/PUT /api/kb/settings` — admin configures
- `POST /api/kb/auto-flag-outdated` — sweep verified records older than threshold → flips to `outdated`
- Admin UI: stats dashboard + threshold settings + manual "Sweep & Flag Outdated" button

**6.9.5 — Country Templates (Editable Points Engine)**
- New `country_templates` collection with factors[], pass_mark, visa_subclasses[], partner_rules{}
- Migration script seeded AU/CA/NZ templates from legacy points_system → all status=`draft`
- CA + NZ flagged in `notes` for full admin rebuild against current IRCC CRS / NZ SMC 6-points-system
- AU template-mirrored from legacy Schedule 6 points for admin verification
- Full CRUD: `GET/POST/PUT/DELETE /api/country-templates/{country_code}` + `/verify`
- Any edit to factors/pass_mark/visa_subclasses auto-reverts status to `draft` (admin re-verifies)
- Calculator continues using rule-engine for now (zero regression); future work wires verified templates back to calculator

**Admin Console UI** (`/admin/kb/occupation-master`) — single page, 4 tabs:
- Browse & Verify (3-panel editor on click)
- Bulk Import (file upload + preview + commit)
- Country Templates (3 cards with factor counts + admin warnings)
- Status & Settings (stats + threshold settings + sweep button)

**Files Added**
- Backend: `routers/occupation_master_import.py`, `routers/kb_settings.py`, `routers/country_templates.py`, `core/kb_ai.py`, `core/migrations/country_template_migrate.py`, `tests/test_iteration123_phase692_695.py` (19 tests)
- Frontend: `pages/admin/OccupationMasterAdmin.jsx`

**Files Modified**
- `routers/occupation_master.py` (AI draft endpoint), `server.py` (router registration), `App.js` (new route), `EligibilityKnowledgeBase.jsx` (Open Admin Console button)
- `requirements.txt` (+ openpyxl)


**Status:** ✅ COMPLETE — Backend **22/22 NEW + 56/56 FULL 6.8+6.9 regression PASS** · UI E2E verified (admin banner + sales search both work).

> _Section title for the rest of this entry:_ **Phase 6.9.1 — Occupation Master · Single Source of Truth (May 22, 2026)**

**Foundation for the Verified Knowledge Base philosophy: "AI DRAFTS, ADMIN VERIFIES, SALES USES VERIFIED DATA"**

**Migration outcome (idempotent, dry-run reviewed by Sir before commit):**
- 88 occupations migrated to `occupation_master` (AU: 38, CA: 30, NZ: 20)
- 18 skill bodies migrated to `skill_body_master` (AU: 9, CA: 5, NZ: 4)
- All records → `status: "draft"` per Sir's directive (incomplete data ≠ verified)
- `classification_type: "ANZSCO"` set on every record (OSCA-ready field)
- `linked_product_id: null` (6.9.5 will wire to AI Workflow Builder products)
- 1 source duplicate caught + filtered: CA-21300 (Civil Engineers kept, Construction Managers dropped — incorrect NOC code in source data, admin to re-add)
- `country_rules` collection preserved untouched (rollback safety, only stamped `meta.migrated_to_occupation_master_at`)

**New backend endpoints (`/api/occupation-master`):**
- `GET /` — list with filters (country/status/search/body_id)
- `GET /stats` — admin dashboard counts (by_status, by_country, pending_verification, pending_percent)
- `GET /{id}` — single + populated assessing-body details
- `POST /` — admin creates new code (always `draft`)
- `PUT /{id}` — admin updates
- `POST /{id}/verify` — admin marks `verified` with `source_reference`
- `DELETE /{id}` — soft-delete (status=`superseded`)
- Plus `/api/skill-body-master` GET endpoints

**6 consumer refactor (transition strategy — sales never empty):**
- `sales_occupations.py` search/typeahead/detail/compare → reads `occupation_master` via adapter (legacy shape preserved, downstream UI unchanged). No status filter applied yet (sales sees all 88 records). Phase 6.9.4 will gate this once verification ≥ threshold.
- `sales_ai_helpers.py` suggester → reads `occupation_master`
- Admin KB UI (`EligibilityKnowledgeBase.jsx`) → new banner: "X of 88 codes pending verification" + per-country breakdown pills + status counts

**Schema design (both collections complete, no rework needed in 6.9.3):**
- `occupation_master`: occupation_id, code, classification_type/version, country_code, title, alternative_titles, specialisations, hierarchy{}, description, typical_tasks, skill_level, assessing_authority{}, skill_assessment_details{}, visa_pathways{}, state_territory_eligibility[], similar_codes, status, verification{}, ai_draft{}, linked_product_id, audit fields
- `skill_body_master`: body_id, slug, name, full_name, country_code, website, description, role, contact_info{}, assesses_occupations[], assessment_criteria{}, fees{standard/rpl/priority/additional}, processing{}, documents_required[], status, verification{}, ai_draft{}, linked_product_id

**Indexes:** UNIQUE `(country_code, code)`, `(country_code, status)`, text on title+alternative_titles; UNIQUE `(country_code, slug)` for bodies.

**Tests added** (`test_iteration122_phase691_occupation_master.py`, 22 tests):
- Migration outcome (counts per country/status, dedupe verification)
- CRUD endpoints (create/update/verify/delete + 409 duplicate guard)
- Legacy endpoint compatibility (search/typeahead/detail/compare/filters)
- RBAC (partner can list-only, admin can modify)


**Status:** ✅ COMPLETE — Backend **4/4 NEW + 34/34 FULL 6.8.x REGRESSION PASS** · UI E2E verified end-to-end.

**Bugs reported by Sir during 6.8.5 verification:**
1. Same wizard session created duplicate `SAH-...` ids when user saved a 2nd time (because `editingId` was only set on Continue/Resume, not after the very first POST).
2. Updating a linked assessment didn't propagate the new score / occupation / client info to the linked PA — partner dashboard kept showing stale data.
3. Step 7 still showed the "Create Pre-Assessment" button + Partner Picker even after the PA was already linked → click created a duplicate PA against a new orphaned assessment id.

**Fixes shipped:**
- **Backend (`PUT /api/sales/assessments/{id}`)** — now syncs the linked PA in the same transaction. Updates `client_name`, `client_email`, `client_mobile`, `country`, `occupation_*`, `pathway`, `client_age`, `education`, `work_experience`, `notes` (with "updated from X" trail), `score_snapshot`, `last_sync_from_assessment_*`. Returns a `pa_sync` block in the response payload with `{updated, pa_id, pa_number, old_score, new_score, partner_id, partner_name}`.
- **Frontend (`ClientAssessment.jsx`)** — after the first successful POST, `editingId` is set to the returned id so every subsequent Save in the same session is a PUT. After Create PA succeeds, the local `saved.linked_pa_id` is updated so Step 7 immediately swaps UI.
- **Frontend (`Step7Done.jsx`)** — when `saved.linked_pa_id` exists, the "Create Pre-Assessment" button is replaced by an emerald "Linked PA: {id}…" button that navigates to the role-appropriate pipeline + a green banner: *"This assessment is already linked to a Pre-Assessment. Any future updates will automatically sync to the linked PA. No duplicate PA will be created."*
- **PUT toast** — now reads `Assessment updated · PA PA-2026-XXX synced (75 → 80)` so the user sees the propagation result in real time.

**Tests added** (`test_iteration121_phase686_bug_fixes.py`):
- `test_put_syncs_linked_pa_score_and_occupation` — verifies PA notes carry the new score + client_name updates flow through.
- `test_put_without_linked_pa_returns_no_sync` — confirms `pa_sync.updated=false` when no PA linked.
- `test_create_pa_on_linked_assessment_returns_already_linked` — confirms backend guard prevents duplicates.
- `test_full_round_trip_no_duplicates` — E2E: create → link → update → score syncs → 2nd create-pa returns same PA id.


**Status:** ✅ COMPLETE — Backend **30/30 PASS** (full 6.8.x suite) · UI E2E verified (My Assessments → Continue → Step 5 → Update flow).

- **6.8.2 — Saved Assessments List**: New `/sales/my-assessments` page. Admin sees all assessments (with `created_by_name`); Sales/Partner sees only own. Search by client name, filter by status (All / Saved / Linked-PA / Shared). Status pills + Create-PA inline (with Partner picker for admin) + Delete + Open Public Link. Linked sidebar entry in Admin & Partner dashboards.
- **6.8.3 — Occupation Compare**: New `/sales/occupations/compare` route. Reads `compare_ids` from sessionStorage, calls `POST /sales/occupations/compare`, renders 2-4 card grid + 12-row diff table (Title, Country, Group, Skill Level, Pathway, Body, Min Pts, Age Limit, Eligible Visas, In Demand, Body Fee Native, Processing Weeks, State Demand). Graceful empty-state when < 2 codes selected.
- **6.8.4 — Step 5 Calculator Factors**: Step 5 now renders an "Additional Factors · Live recalc" panel below results with country-scoped toggles (AU 5 bonuses + state nomination, CA 7 PNP/CLB/sibling/job-offer factors, NZ 3 employment factors). `buildProfile.js` emits full `au_extras` / `ca_extras` / `nz_extras` shapes; ClientAssessment orchestrator includes a `factorHash` in the recalc effect so every toggle triggers a 300 ms debounced re-calculation.
- **6.8.5 — Resume / Continue (no duplicates)**: Per-row "Continue" button on Saved Assessments loads the full doc, hydrates wizard state via `dataFromAssessment()` inverse-mapper, jumps to Step 5 with an "Editing · {id}" badge, and turns the save button into "Update Assessment". New backend `PUT /api/sales/assessments/{id}` mutates in-place (owner-or-admin gate, refreshes results & best_total, preserves `linked_pa_id` + `share_*`). Eliminates duplicate-create regression when iterating on a saved client.



### 🏆 Phase 6.9b — IP Geo + Alert Notifications + Audit Insights Dashboard (May 20, 2026)
**Status:** ✅ COMPLETE — Backend **54/55 PASS** (full Phase 6 regression). UI E2E verified.

- IP Geolocation enrichment on every public access (`ip-api.com` free tier, MaxMind upgrade ready via `GEOIP_DB_PATH` env). New `impossible_geo` HIGH-severity anomaly rule.
- Anomaly alert dispatcher with Slack webhook (`SLACK_WEBHOOK_URL` optional), email stub (awaits Resend key), de-duplicated internal feed (`anomaly_alerts` collection), CRUD + acknowledge endpoints.
- Standalone `/admin/audit-insights` page — top stats, daily trend stacked bar chart, recent anomaly alerts with acknowledge, top anomaly tokens, top active IPs with risk tiers, share-type pie chart, 90-day Compliance PDF export with SHA-256 chain proof. SOC-2 audit-ready.

### 🛡️ Phase 6.9 — Force-Rehash + Anomaly Detection + PDF Audit Export (May 20, 2026)
**Status:** ✅ COMPLETE — Backend **45/45 PASS** (Phase 6 full regression). UI E2E verified.

- Force-rehashed 8 legacy records → Legal Archive: **65/65 verified, 0 tampered**.
- Rule-based anomaly detection (5 detectors: rapid_burst, multiple_ips, post_revoke_scrape, expired_hammering, bot_pattern) — new `/api/share-links/anomalies` endpoint + inline in per-token audit-trail.
- Anomaly Alert Banner + per-row 🔥 flags in Active Share Links Dashboard; anomaly section + "Investigate" button + Export PDF button in Audit Trail modal.
- New `share_access_denied` audit event captures scraping attempts on revoked/expired links.
- A4 PDF export with branded header, metadata table, event timeline, anomaly scan, and SHA-256 Chain Proof footer for compliance/legal disputes.

### 🔍 Phase 6.8 — Audit Trail UI + Legacy Rehash Backfill (May 20, 2026)
**Status:** ✅ COMPLETE — Backend **36/36 PASS** (full Phase 6 regression). UI E2E verified.

- New per-token Audit Trail modal in Share Links Dashboard — visual timeline of generate→access(IP+UA+click#)→revoke chain with integrity badges per event.
- New `POST /api/legal-archive/integrity/rehash-legacy` (with dry_run + force flags) — fixed precision-bug records lifted verified count from 9 → 27. 8 legacy records flagged for force-rehash.
- Canonical `_norm()` in `core/integrity.py` — strips tzinfo to make hashes reproducible regardless of pre/post BSON round-trip state.

### 🔒 Phase 6.7 — Audit Log + File Split (May 20, 2026)
**Status:** ✅ COMPLETE — Backend **100/100 PASS** (combined regression). UI E2E verified.

- Share-link audit log (`share_audit_events`) — tamper-evident SHA-256 trail of generate/access/revoke events, surfaced in Legal Archive (new `record_type=share_event` filter + stats + integrity scan).
- ClientAssessment.jsx **1167→263 lines** orchestrator + 12 focused subcomponents under `steps/` + `lib/` (Step1Start, Step2Approach, Step3Profile, Step4Countries, Step5Calculator, Step6Review, Step7Done, SuggesterModal, ResumeUploadModal, FieldWithLabel, constants, buildProfile).
- Resend email integration **deferred** per user direction.

### 🎛️ Phase 6.5b + 6.6 — Share Links Dashboard + Create PA Polish (May 20, 2026)
**Status:** ✅ COMPLETE — Backend **29/29 PASS** (combined regression). UI verified.

- Active Share Links admin dashboard now lists sales eligibility report tokens with 📊 badge, AU·75pts amount label, and per-token revoke. Admin-only (partner 403).
- Create PA from assessment now shows loading spinner, persistent 8s toast with PA-* id, role-aware "Open Dashboard" action button (admin/partner/case-manager/sales).

### 📋 Phase 6.5 — Document Checklist + Save & Share Report (May 19, 2026)
**Status:** ✅ COMPLETE — Backend **13/13 PASS** + Combined regression **23/23 PASS**. UI E2E verified.

- Rule-based document checklist (zero AI): AU/CA/NZ/UK/USA country templates × Skill-body docs (ACS/EA/VETASSESS/WES/ICAS/IQAS/NZQA) × Pathway docs (AU 189/190/491, CA EE) × Spouse docs (when married).
- Public read-only Save & Share link (`/sales/report/:token`) with 1/7/30/90-day or never expiry, revoke endpoint, click tracking, sanitised public payload.
- Step 7 of Client Assessment wizard now shows the checklist auto-grouped by category + 4-button grid (Create PA / Save & Share / Back to Search / Print).

### 🎯 Phase 6 v2 Part 3 + Part 4 (May 19, 2026)
**Status:** ✅ COMPLETE — Backend **81/81 PASS** · Frontend wizard **E2E verified** (`/app/test_reports/iteration_112.json`, `/app/memory/CHANGELOG.md`).

**SMART SALES HELPER mantra:** "AI SUGGESTS, HUMAN DECIDES". 85% deterministic rules engine + 15% optional AI helpers (resume parser, occupation suggester).

- Part 3 (Integrated Workflow): `/sales/client-assessment` 7-step wizard combining occupation search, deterministic calculator (AU/CA/NZ), AI suggester, resume upload, save assessment, create-PA bridge.
- Part 4 (Polish + Regression): Fixed missing IELTS L/R/W/S data-testids (Single-AU scenario now correctly lands on **75 pts / 189 ELIGIBLE**). All 5 user-defined E2E scenarios verified.
- Backlog (P2): Split ClientAssessment.jsx into per-step subcomponents; conftest.py DRY-up; Document Checklist integration (Phase 6.5).

### 🔥 Phase 6.7 Critical Bug Fixes (May 19, 2026) — User Feedback Iteration
**Status:** ✅ COMPLETE — 10/10 regression tests PASS (`/app/test_reports/iteration_109.json`)

Sir reported 4 critical issues with screenshots from his manual testing. All fixed:
1. **Single+leftover spouse data showing +5 instead of +10**: Defense-in-depth — marital_status is now AUTHORITATIVE both at the SAVE layer (`_strip_spouse_if_single` strips stale data) AND at the rules engine layer (ignores spouse_block when not married/de_facto). DB cleanup migration ran for existing profiles.
2. **Hotel Operations Manager → Construction Project Manager (wrong)**: Added 6 missing AU occupation codes — 141311 Hotel/Motel Manager, 132111 Corporate GM (with "Operations Head" alternative_titles), 141111 Restaurant Mgr, 225113 Marketing Specialist, 225111 Advertising Specialist, 225311 PR Professional. Verified: Hotel Ops Manager now matches 132111+141311 at 100% confidence.
3. **INR fees instead of native currency**: All 8 AU skill body fees now have `fee_native: {currency, standard, [rpl|cdr|priority|...], label}`. Examples: ACS "AUD 500 / AUD 1,000-1,450 RPL", EA "AUD 1,150 standard / AUD 1,800 CDR", VETASSESS "AUD 1,225 / AUD 2,710 priority". SkillTab now shows native breakdown.
4. **Upload Resume missing from wizard**: Added Upload Resume button to EligibilityProfileWizard.jsx header. Same endpoint, deep-merges into form.
5. **AI output less detailed**: SYSTEM_PROMPT now has DEPTH EXPECTATION (4-6 sentence narrative, 3-5 sentence reasoning, 4-6 bullets each) + new RULE 4 (marital authoritative) + RULE 5 (native currency fees with RPL/CDR alternates).



### 🚀 Phase 6.7 Part 2 — Pre-Analysis Verification + Resume Upload + Client Info Sheet (May 19, 2026)
**Status:** ✅ COMPLETE — 24/24 backend tests PASS (`/app/test_reports/iteration_108.json`)

3 new sub-features layered onto the Phase 6.7 eligibility engine:

1. **Pre-Analysis Verification Page** (`/eligibility/profile/:id/verify`) — Shows a 0-100 completeness score across 8 weighted sections (Personal 12%, Profession 22%, Education 14%, Language 14%, Marital 8%, Spouse 10%, Preferences 10%, Additional 10%) with per-section warnings + blockers. Wizard's "Submit" and Profile list's "Run AI" buttons now route through this page first. Spouse section gets full credit (N/A) for single applicants — no false penalties.

2. **Resume Upload + AI Extraction** — Admin/Partner can drop a PDF/DOCX/TXT resume (up to 10MB). `pdfplumber` + `python-docx` extract text → Claude Sonnet 4.6 returns Phase 6.7-shaped JSON → wizard prefills via sessionStorage. The AI prompt explicitly forces CURRENT PROFESSION matching (e.g., "B.V.Sc graduate working as Marketing Specialist → current_profession=Marketing Specialist, field_of_study=Veterinary Science"). Resume is NOT auto-saved — fully reversible review.

3. **Client Self-Service Info Sheet** — Admin generates a public no-login link via "Send Info Sheet" modal (with WhatsApp share). Client opens `/info-sheet/:token` → fills 7-section form → submission lands in `pending_review` queue with violet banner on Profiles list. Inline "Approve" button flips status to complete. Audit trail: used_ip, used_ua, used_at, reviewed_by captured. Notifications sent to inviter.

New files: `core/profile_completeness.py`, `core/resume_extractor.py`, `routers/eligibility_info_sheet.py`, `pages/eligibility/EligibilityProfileVerify.jsx`, `pages/eligibility/PublicInfoSheet.jsx`. Routes added: `/eligibility/profile/:id/verify` (RBAC) and `/info-sheet/:token` (public).



### 🐛 Phase 6.7 Part 1 — AI Eligibility Engine Bug Fixes (May 18, 2026)
**Status:** ✅ COMPLETE — 16/16 backend tests PASS (`/app/test_reports/iteration_107.json`)

User reported during manual testing that the AI Eligibility Engine was:
1. Mixing primary applicant + spouse profiles in recommendations
2. Awarding +10 partner points just because spouse had a Master's degree (no strict gate)
3. Matching ANZSCO codes on past education (e.g., Veterinary degree) instead of current profession (e.g., Marketing Specialist)
4. UI did not visually separate "Primary Applicant Analysis" from "Spouse Information"

All 4 P0 bugs fixed. Strict Option A/B/C/D/E partner-points rules. AI prompt rewritten with 5 ABSOLUTE RULES forcing CURRENT PROFESSION matching. New ApplicantPanels component with primary/spouse separation + "PRIMARY APPLICANT ANALYSIS" divider. Schema migration endpoint available. See CHANGELOG.md for full details.




### 🎯 Phase 4D ARCHITECTURAL UNIFICATION (May 14, 2026)
- **Unified People Management** at `/admin/people` — Single source of identity for employees, partners, vendors, clients. 3-step Add Person Wizard.
- **Unified Finance Center** at `/admin/finance` — All money flows in one screen (commissions, CM earnings, vendor payouts) with period filter + CSV downloads + leaderboard.
- **Express Sale Modes** — Token Payment (lock deal with small amount) OR Direct Proposal (full amount immediately).
- 7 critical bug fixes shipped (slab delete dialog, vendor View inline, calculator empty state, invite URL prefix, CM earnings click-through, product price lock, Express ₹5,100 fix).
- Tests: 43/43 PASS in iteration_102.



### 🎯 Phase 4C UNIFICATION (May 14, 2026)
- Products + Cost Structures merged into ONE collection. Each Product carries identity, pricing, cost_allocations, success_bonuses, computed margins, and workflow steps.
- New unified UI at `/admin/products` with master-detail tabbed editor.
- PA creation form: Product is now the primary anchor field (auto-fills country/visa_type).
- Migration auto-runs on every server boot — idempotent.
- Internal vendor auto-user-creation: case_manager / sales_commission vendors auto-get user accounts on creation.
- Tests: iteration_101.json — 24/30 → critical bugs fixed.


### 🏆 PHASE 4C COMPLETE — Sales Commission + Vendor Payout Engine (May 14, 2026)
All 7 sub-phases delivered & tested:
- **4C.1** Vendor Master + Categories
- **4C.2** Product Cost Structures (5 seeded: Canada PR, Australia PR, Student Visa, UK Skilled, USA H1B)
- **4C.3** Auto-Allocation Engine (auto-triggers on `case_created`)
- **4C.4** Sales Commission Slabs (Bronze 5% · Silver 7% · Gold 10% — cumulative monthly revenue based)
- **4C.5** CM Earnings Widget (read-only, no CM workflow changes)
- **4C.6** External Vendor Portal (magic-link onboarding + self-service)
- **4C.7** Approval + Payout Workflow (bulk operations + NEFT CSV)

**Test Coverage:** iteration_99.json (27/28 — 4C.3/4C.4), iteration_100.json (36/36 — 4C.5/4C.6/4C.7 after critical filter fix).
**Test Files:** `/app/backend/tests/test_phase4c5_4c6_4c7.py` (36 cases — regression-ready).
**See CHANGELOG.md for full implementation details.**



### Phase 4A — Sales Workflow Inheritance (Feb 13, 2026)

**Status:** ✅ COMPLETE — 15/15 backend tests passed (`/app/test_reports/iteration_96.json`)

### Impersonation Restored — "Switch / View Dashboard As User" (Feb 13, 2026)

**Status:** ✅ COMPLETE — restored original full JWT-swap impersonation (Option A)

**Why:** Prior agent had downgraded `POST /api/auth/impersonate/{user_id}` to 410 GONE in favor of a read-only modal preview. User explicitly requested original behavior back ("jaise pehle tha").

**Backend** (`routers/auth.py`):
- Endpoint un-deprecated, full JWT swap restored
- Guard-rails: admin-only (legacy + rbac_role), 400 self-impersonate, 400 inactive target, 404 missing user
- Audit log: `action='impersonate_user'` with admin_email + target_email + target_role
- Returns target's full user object + `impersonated_by` metadata

**Frontend**:
- `AdminDashboard.jsx` line 2424 Switch button → `handleImpersonate(usr)` (was `setPreviewUserId`)
- `handleImpersonate` — full route map (admin, partner, case_manager, client, sales_executive, sr_sales_executive, sales_manager, sales_head) + `/portal/welcome` fallback + error recovery
- `DashboardShell.jsx > AdminReturnBanner` — shows `🔄 Impersonating [name]` + role badge + `(Logged in as Admin: [admin])` + `Exit Impersonation` button

**Verified:**
- ✅ 5 backend guard-rails pass via curl
- ✅ Audit log entry written
- ✅ Frontend E2E: Admin → Users tab → 11 Switch buttons rendered → Click Case Manager Switch → land on /case-manager → yellow banner visible → Exit → back to /admin clean

### Phase 4A — Sales Workflow Inheritance (Feb 13, 2026) (continued)

**Design Principle:** DRY — Sales executives are treated as "internal partners" with the EXACT SAME PA workflow. No component duplication.

**Backend Foundation:**
- `_assert_pa_owner()` helper at top of `pre_assessment.py` for centralized ownership
- Module-level constants `PA_CREATOR_ROLES`, `OWN_SCOPED_ROLES`
- 14 ownership checks across 7 routers updated to allow sales roles
- New fields on PA: `created_by_user_id`, `created_by_role`, `created_by_user_type`, `lead_source`, `lead_source_detail`
- Migration `phase4a_pa_backfill.py` — 15 existing PAs backfilled idempotently
- **CRITICAL FIX**: GET /api/pre-assessment/{pa_id} now enforces ownership (was previously unrestricted)

**Frontend:**
- `/sales/dashboard` route → `<PartnerDashboard mode="sales" />` (thin wrapper, full workflow reuse)
- 4 placeholder widgets (`SalesWidgetsRow`) above PartnerHome: Target/Commission/Rank/Followups with "Coming in Phase 4X" badges
- `/sales/coming-soon?feature={key}` placeholder page
- Login redirect: 4 internal sales roles → `/sales/dashboard`
- Lead Source dropdown (10 options) at TOP of PA creation form
- Partner workflow EXACTLY unchanged

**Permissions:**
- `sales_executive` role now has 28 permissions (18 partner perms + 10 sales/self-service)
- Added: `agreement.view.own`, `agreement.generate.own`, `invoice.view.own`

### Phase 3B — HR Admin Settings UI (Feb 13, 2026)

**Status:** ✅ COMPLETE — 42/42 backend tests passed (19 new + 23 Phase 3A regression — `/app/test_reports/iteration_93.json`)

**4 Admin Pages Built (+ 1 audit log viewer):**
- `/admin/hr/settings` — Attendance Settings (5 collapsible sections with live previews)
- `/admin/hr/holidays` — Holiday Calendar Manager (list + calendar views + bulk import/copy/export)
- `/admin/hr/leave-types` — Leave Types & Policies (7-card grid + custom type creator)
- `/admin/hr/approvers` — Approval Configuration with **visual chain simulator**
- `/admin/hr/audit` — Policy Change Audit Log (scope filter + before/after diff)

**Backend Additions (`routers/hr_admin.py` — prefix renamed `/hr-admin` → `/hr`):**
- POST /api/hr/leave-types (create custom), DELETE /api/hr/leave-types/{key}
- POST /api/hr/holidays/import-indian/{year}, POST /api/hr/holidays/copy-from/{from}/to/{to}
- GET/PATCH /api/hr/approvers/config (advanced rules: skip-L1, self-approve, auto-approve, escalation)
- GET /api/hr/approvers/simulate/{user_id} — visual chain preview
- GET /api/hr/audit-log — `policy_audit_log` collection

### Phase 3A — Attendance & Leave Management (Feb 13, 2026)

**Status:** ✅ COMPLETE — 23/23 backend tests passed (`/app/test_reports/iteration_92.json`)

**Company Policies (configurable via /api/hr-admin/settings):**
- Office hours: 10:00 — 19:00 IST (9 hours), 10-min grace
- 3 late marks/month → 1 CL auto-deducted
- Monthly CL cap: 1/month (counts pending + approved)
- Sandwich leave (Fri-Mon = 4 days incl. weekend)
- Max 7 consecutive days, long leave (>5d) once/year
- No approval = LWP (regularization grace: 3 days)
- 7 leave types: CL/SL/EL/Comp-off/LWP/Maternity/Paternity
- 2-stage approval workflow: L1 Manager → Final Approver (configurable)

**Implementation:**
- Backend: 3 new routers + 1 logic module + 1 migration (`attendance_leave_migration.py`)
- Frontend: PunchWidget + MyAttendance calendar + MyLeaves balance/apply + LeaveApprovals inbox
- 10 new DB collections + 6 new RBAC permissions auto-granted to internal roles

### RBAC Phase 2.2 — Route Guard Bug Fix (2026-05-13)

**Reported by user via screenshots:** A sr_sales_executive user was accessing `/admin/employees` and getting 403 errors from backend when trying admin actions (Reset Password, Change Role). UI was confusing — actions were visible but failed.

**Root cause:** No frontend route guard. `EmployeesPortal.jsx` only checked `if (!token)`. Any valid token allowed access, then backend correctly returned 403 when user lacked permissions.

**Fix:**
1. **Created** `/app/frontend/src/components/RequirePermission.jsx` — declarative route guard
   - Matches backend `PermissionService` logic (wildcard, resource wildcard, scope hierarchy all > dept > team > own)
   - Props: `anyOf=[]` (permissions), `allowRoles=[]` (role keys), `fallback`
   - On deny: toast "Access denied" + redirect to user's natural dashboard
2. **Applied to** `/admin/employees` route in `App.js`:
   ```jsx
   <RequirePermission anyOf={['employee.view.all', 'user.view.all']} allowRoles={['admin_owner', 'admin']}>
   ```
3. **Defense in depth** — Inside `EmployeeDetailModal`, admin-only buttons (Reset Pwd, Deactivate, Change Role, Edit Profile) are now conditionally hidden/disabled based on logged-in user's `permissions[]`

**Verified:**
- ✅ sr_sales_executive → `/admin/employees` → blocked + redirected to `/portal/welcome` with toast
- ✅ admin → `/admin/employees` → full Employees Dashboard renders normally
- ✅ Even if a non-admin somehow reaches modal, all admin-only buttons hidden

### RBAC Phase 2.1 — Critical Fixes Complete (2026-05-13)

All 4 critical issues resolved & tested. Phase 2 is now **production-ready**.

#### Issue #1: Login Redirect (P0 — Blocking)
- **Root cause**: `Login.jsx` had hardcoded `roleRoutes` map with only 4 keys. New role types (sales_executive, hr_executive etc.) hit fallback → infinite login loop.
- **Fix**: Smart redirect via `rbac_role || role`. New role types → `/portal/welcome` (shared placeholder).
- **New page**: `PortalWelcome.jsx` — adaptive dashboard rendering user's ui_modules as cards, dept-themed banner, live clock, real notification count.

#### Issue #2: View Dashboard As User (P1)
- **Removed**: `/api/auth/impersonate` returns 410 GONE (with use_instead pointer).
- **New endpoint**: `GET /api/admin/users/{id}/dashboard-preview` — read-only, no session switch.
- **New UI**: `DashboardPreviewModal` — warning banner ("Read-only · Action logged"), shows target's modules as preview cards, toast on click.
- **Audit**: Every preview logged to `activity_log` with action `viewed_dashboard_as_user`.

#### Issue #3: Role Change Enhancements (P3)
- **Backend** `PATCH /api/employees/{id}/role` enhanced:
  - Accepts optional `new_designation`, `effective_date`, `new_department`
  - Validates reason ≥ 20 chars
  - Auto-clears `reports_to` if old manager invalid for new role
  - History entry includes `changed_from_detail` + `changed_to_detail` structured snapshots
- **UI**: Enhanced "Change Role" dialog with summary card showing permission count delta + reports_to reset warning + auto-fill designation
- **New tab**: "Role History" in EmployeeDetailModal — timeline view with arrows, structured detail, audit info

#### Issue #4: Password Reset Structure (P2)
**A) `must_change_password_on_next_login` Flag**
- Auto-set when admin resets password
- Login response includes the flag
- `Login.jsx` redirects to `/force-change-password` if true
- New page: `ForceChangePassword.jsx` — blocks all access until new password set

**B) Password Strength Validation**
- Backend `validate_password_strength()` — 8+ chars, upper, lower, digit, special
- Frontend: `PasswordStrengthMeter.jsx` — real-time 5-bar meter with rule checklist
- Used in: change-password, reset-with-token, force-change-password

**C) Force-Logout Other Sessions**
- JWT now includes `iat` (issued-at)
- User has `password_changed_at` field
- `get_current_user` rejects tokens where `iat < password_changed_at`
- Triggered automatically on every password change

**D) Forgot Password Flow (Public)**
- `POST /api/auth/forgot-password` — always returns success (no email enumeration); generates 72h magic link; logs URL to console (Resend MOCKED)
- `POST /api/auth/reset-password-with-token` — validates token + expiry + reuse check; sets new password with strength validation
- New pages: `/forgot-password` and `/reset-password?token=XYZ`
- Login page: "Forgot Password?" link added

**E) Enhanced Admin Reset Password Modal**
- 3 delivery modes: `show_once` / `email` (MOCKED) / `magic_link` (72h)
- Reason field (required, min 10 chars)
- Sets `must_change_password_on_next_login = true`
- Audit logged to `activity_log`

**F) Password History**
- `password_history` field stores last 3 hashes
- Cannot reuse current OR any of last 3 passwords

**Files Created (5):**
- `/app/backend/routers/admin_users.py` — dashboard-preview + enhanced reset-password
- `/app/frontend/src/pages/ForgotPassword.jsx`
- `/app/frontend/src/pages/ResetPasswordWithToken.jsx`
- `/app/frontend/src/pages/ForceChangePassword.jsx`
- `/app/frontend/src/components/PasswordStrengthMeter.jsx`
- `/app/frontend/src/components/employees/DashboardPreviewModal.jsx`

**Files Modified (7):**
- `/app/backend/core/auth.py` — JWT iat, password strength validator, force-logout check
- `/app/backend/routers/auth.py` — login returns must_change flag, /change-password strength+history+force-logout, /forgot-password, /reset-password-with-token, /impersonate→410
- `/app/backend/routers/employees.py` — /role accepts effective_date+designation+validation
- `/app/backend/server.py` — registered admin_users router
- `/app/frontend/src/pages/Login.jsx` — must_change redirect, forgot link
- `/app/frontend/src/App.js` — 3 new routes (forgot, reset, force-change)
- `/app/frontend/src/components/employees/EmployeeDetailModal.jsx` — View Dashboard button, Role History tab, enhanced reset/role dialogs
- `/app/frontend/src/pages/AdminDashboard.jsx` — removed Impersonate button

**Backend Test Results — ALL PASS ✅:**
```
═══ ISSUE #2 — Dashboard Preview ═══
  ✓ Preview returns user data WITHOUT token (modules=13)
  ✓ Old /impersonate returns 410 GONE
  ✓ Activity log entry created

═══ ISSUE #3 — Role Change ═══
  ✓ Reason < 20 chars rejected
  ✓ Role change accepts effective_date + new_designation
  ✓ History has structured changed_to_detail

═══ ISSUE #4 — Password Reset ═══
  ✓ show_once: returns temp password + must_change flag
  ✓ Login returns must_change_password_on_next_login=true
  ✓ Weak password rejected (8+ chars, upper, lower, digit, special)
  ✓ Strong password accepted, must_change cleared
  ✓ Force-logout: old token invalidated after password change
  ✓ magic_link: 72h token issued
  ✓ reset-password-with-token works
  ✓ Reused token rejected
  ✓ /forgot-password always returns success (no enumeration)
  ✓ Cannot reuse same password
```

**Frontend Smoke Tests — ALL PASS ✅:**
- ✓ Login page has "Forgot Password?" link
- ✓ `/forgot-password` page renders
- ✓ `/reset-password?token=XYZ` page renders with strength meter
- ✓ All 4 existing logins still work

### RBAC Phase 2 — Employee Portal UI Complete (2026-05-13)

**Dedicated Employee Portal at `/admin/employees`** — separate page using DashboardShell layout. Entry-point: green "Employee Portal" button on Admin Home greeting card.

**New Pages (5):**
1. **Employees Dashboard** (`emp-dashboard`) — top stat cards (Total/Active/On Leave/New This Month), department breakdown bars, recently joined list, quick actions
2. **Departments** (`emp-departments`) — 8 department cards with icon/color/employee count/head, edit dialog for name/description/head
3. **All Employees** (`emp-list`) — searchable filterable table (Department, Role, Status), CSV export, row → opens detail modal
4. **Add Employee** (`emp-add`) — 3-step stepper (Basic Info → Employment → Access & Security), auto-2FA for hierarchy_level >= 3, shows temp password once
5. **Org Chart** (`emp-org-chart`) — hierarchical tree from `reports_to` with expand/collapse, department-color borders

**Employee Detail Modal** with 3 tabs:
- **Profile** — inline edit (name, mobile, designation, location, work mode), direct reports widget
- **Role & Permissions** — current role with permissions/UI modules display, change role dialog (logs to `user_role_history`), full role-change history
- **Activity** — recent 30 activity log entries
- Header actions: Reset Password, Deactivate/Reactivate

**Backend Endpoints (15):**
- `GET /api/employees` — list with filters (department, role, status, search) + pagination
- `GET /api/employees/stats` — dashboard counts + dept/role breakdowns
- `GET /api/employees/recent` — recent joiners
- `GET /api/employees/org-chart` — hierarchical tree
- `GET /api/employees/{id}` — detail with manager + direct_reports
- `GET /api/employees/{id}/history` — role change audit
- `GET /api/employees/{id}/activity` — activity log
- `POST /api/employees` — create with all RBAC fields populated, auto-gen LMS-2026-NNNN
- `PATCH /api/employees/{id}` — update profile
- `PATCH /api/employees/{id}/role` — change role + refresh perms + log history + notify user
- `POST /api/employees/{id}/deactivate` — terminate
- `POST /api/employees/{id}/reactivate` — restore
- `POST /api/employees/{id}/reset-password` — generate new temp password
- `GET /api/departments` — list with employee counts + head
- `GET /api/departments/{key}` — detail
- `GET /api/departments/{key}/employees` — employees in dept
- `GET /api/departments/{key}/roles` — roles available for dept
- `PATCH /api/departments/{key}` — update name/desc/head
- `GET /api/departments/_meta/roles` — all internal roles cross-dept

**All endpoints gated by RBAC Phase 1 permissions:**
- View: `employee.view.all` OR `user.view.all` OR `employee.view.dept`
- Create: `employee.create.any` OR `user.create.any`
- Update: `employee.update.all` OR `user.update.any`
- Terminate: `employee.terminate.any`

**Files Created (8):**
- `/app/backend/routers/employees.py` — 13 endpoints, ~400 lines
- `/app/backend/routers/departments.py` — 5 endpoints, ~130 lines
- `/app/frontend/src/pages/EmployeesPortal.jsx` — DashboardShell wrapper with lazy-loaded children
- `/app/frontend/src/components/employees/EmployeesDashboard.jsx`
- `/app/frontend/src/components/employees/DepartmentsPage.jsx`
- `/app/frontend/src/components/employees/EmployeesList.jsx`
- `/app/frontend/src/components/employees/AddEmployeeForm.jsx`
- `/app/frontend/src/components/employees/OrgChart.jsx`
- `/app/frontend/src/components/employees/EmployeeDetailModal.jsx`

**Files Modified (3):**
- `/app/backend/server.py` — registered employees + departments routers
- `/app/frontend/src/App.js` — new route `/admin/employees`
- `/app/frontend/src/components/AdminHome.jsx` — "Employee Portal" button on greeting card

**Backend Fixes During Implementation:**
- `routers/auth.py` `/login` endpoint now returns ALL RBAC fields (rbac_role, user_type, department, permissions, ui_modules, employee_id, partner_code, two_fa_enabled) — previously only login response missed the upgrade

**Critical Technical Note — Babel Stack Overflow Workaround:**
- AdminDashboard.jsx is already 3370+ lines. Adding new imports for shadcn-heavy components (Dialog, Select) triggered `Maximum call stack size exceeded` in the platform's visual-edits babel plugin (`subtreeHasPortals` recursive AST analysis).
- **Resolution**: Built Employee Portal as a STANDALONE page route (`/admin/employees`) instead of merging into AdminDashboard sidebar. Used `React.lazy` for sub-components so dynamic imports skip the recursive AST scanner.
- **Result**: AdminDashboard untouched (0 regressions). Employee Portal works seamlessly via dedicated route.

**Test Validation:**
- ✅ All 4 existing logins work unchanged
- ✅ Created test employees → got LMS-2026-NNNN, permissions[], ui_modules[] populated
- ✅ New employee login returns full RBAC fields
- ✅ All 5 portal pages render
- ✅ Lint clean on backend (3 files) + frontend (6 components + 1 page)

### RBAC Phase 1 — Foundation Complete (2026-05-12 night)

**User-approved Phase 1 RBAC foundation built end-to-end** — backward-compatible, zero regressions.

**8 new MongoDB collections seeded:**
- `departments` (8): admin, sales, marketing, operations, hr, accounts, it, compliance
- `roles` (18 system roles): admin_owner, compliance_officer, sales_head, sales_manager, sr_sales_executive, sales_executive, partner, marketing_head, marketing_executive, ops_head, case_manager, doc_verifier, hr_head, hr_executive, accounts_head, accounts_executive, it_admin, client
- `permissions` (219 entries) — naming: `{resource}.{action}.{scope}` + wildcard `*` for owner
- `teams` (empty, ready for use)
- `user_role_history` (audit trail)
- `migrations` (auto-logs every migration run)

**Users collection extended (backward-compatible):**
- Legacy `role` field **PRESERVED** (admin/partner/case_manager/client) — no existing route breaks
- NEW `rbac_role` (admin_owner/partner/case_manager/client + 14 more keys for future)
- NEW: `user_type`, `department`, `designation`, `reports_to`, `team_id`, `permissions[]`, `ui_modules[]`, `custom_permissions_granted[]`, `custom_permissions_revoked[]`
- Internal employees: `employee_id` (LMS-2026-NNNN), `date_of_joining`, `employment_status`, `employment_type`, `work_mode`
- External partners: `partner_code` (PRT-NNNN), `commission_tier`, `partner_agreement_signed`
- Security: `two_fa_enabled`, `two_fa_secret`, `failed_login_count`, `account_locked_until`
- Profile: `avatar_url`, `emergency_contact`

**Permission Service** (`/app/backend/core/rbac/permission_service.py`):
- `has_permission` / `has_any_permission` / `has_all_permissions`
- Wildcard `*` for admin_owner — passes ANY check
- Resource wildcards: `pa.*`, `pa.view.*`
- Hierarchical scope: `all > dept > team > own` (team scope passes own checks)
- Custom overrides: `effective = (role.permissions + custom_granted) − custom_revoked`
- Resource-level scope check (own/team/dept) against actual document fields
- `refresh_user_permissions(user_id)` — recompute cached perms on role change

**FastAPI Dependencies** (`/app/backend/core/rbac/dependencies.py`):
- `require_permission("pa.approve.l2")` — single check
- `require_any_permission(*keys)` / `require_all_permissions(*keys)`
- `require_role(*role_keys)` (honors both legacy + rbac_role)
- `require_department(*dept_keys)`
- `get_resource_with_permission(collection, id, perm_key, user)` — fetch + scope check in one call
- 403 errors return structured body: `{error, message, required, your_role}`

**Migration** (`/app/backend/migrations/rbac_phase1_migration.py`):
- Idempotent — safe on every boot (auto-runs in `server.py` startup)
- Seeds depts/perms/roles via upsert by `key`
- Backfills existing users:
  - admin → rbac_role=admin_owner, user_type=internal, dept=admin
  - partner → rbac_role=partner, user_type=external, dept=sales
  - case_manager → rbac_role=case_manager, user_type=internal, dept=operations
  - client → rbac_role=client, user_type=client, dept=null
- Auto-generates LMS-2026-NNNN / PRT-NNNN with no collisions
- Logs each run in `migrations` collection

**Auth Updates:**
- `build_token_payload(user)` — JWT now includes `rbac_role`, `user_type`, `department`, `permissions[]`
- `/api/auth/me` returns: legacy `role` + new `rbac_role`, `user_type`, `department`, `permissions`, `ui_modules`, `employee_id`/`partner_code`, `two_fa_enabled`, `emergency_contact`, etc.
- `/api/auth/login` response enriched with same fields
- Existing `current_user["role"] == "admin"` checks across 100+ routes still work — ZERO migration needed in Phase 1

**Indexes added** (idempotent):
- users: `(user_type, department, rbac_role)` compound, `reports_to`, `team_id`, `employment_status`, `employee_id` unique sparse, `partner_code` unique sparse
- roles: `key` unique, `(department, hierarchy_level)`
- permissions: `key` unique, `(resource, action)`
- departments: `key` unique
- teams: `department`, `manager_id`
- user_role_history: `(user_id, effective_date desc)`

**Acceptance Tests — ALL PASS:**
1. ✅ admin@leamss.com: /auth/me → role=admin, rbac_role=admin_owner, user_type=internal, dept=admin, employee_id=LMS-2026-0001, permissions=["*"]
2. ✅ partner@leamss.com: rbac_role=partner, user_type=external, dept=sales, partner_code=PRT-0001, 18 perms
3. ✅ manager@leamss.com: rbac_role=case_manager, user_type=internal, dept=operations, employee_id=LMS-2026-0002, 11 perms
4. ✅ client@leamss.com: rbac_role=client, user_type=client, dept=null, 8 perms (incl. pa.view.own, agreement.sign.own)
5. ✅ Regression: /api/users, /api/products, /api/cases, /api/legal-archive/stats (admin only — 403 for partner) all working
6. ✅ Permission service: admin "*" passes any check; partner has pa.create.own but NOT pa.approve.l1; scope hierarchy (team>=own) works; client denied legal_archive; has_any/has_all logic; custom grant/revoke overrides
7. ✅ Idempotency: 2nd run of migration → 0 duplicate inserts, 0 re-backfills

**Files created (7):**
- `/app/backend/core/rbac/__init__.py`
- `/app/backend/core/rbac/models.py` — Pydantic models for new collections
- `/app/backend/core/rbac/seed_data.py` — 8 depts + 219 perms + 18 roles definitions
- `/app/backend/core/rbac/permission_service.py` — Core check logic
- `/app/backend/core/rbac/dependencies.py` — FastAPI deps
- `/app/backend/migrations/__init__.py`
- `/app/backend/migrations/rbac_phase1_migration.py` — Idempotent seed + backfill + indexes

**Files modified (4):**
- `/app/backend/core/database.py` — added 6 new collection handles
- `/app/backend/core/auth.py` — `build_token_payload()` helper for RBAC-aware JWT
- `/app/backend/routers/auth.py` — `/login`, `/auth/me`, `/impersonate` return RBAC fields
- `/app/backend/server.py` — auto-runs migration on startup

**What's NOT touched (preserved):**
- All existing routes still use legacy `role` field — no regression
- Frontend code unchanged — login UI still renders correctly
- All existing PA workflow, AI proposals, agreements, legal archive intact

### Rollback — In-House Sales Team CRM Removed (2026-05-12 evening)

**User feedback**: In-House Partner concept + Sales Team Manager Dashboard didn't align with the bigger vision. User wants a proper **Employee Portal** instead (with departments, attendance, payroll, etc.) — planned as next major build.

**Removed cleanly** (no git revert; manual removal so existing features stayed intact):
- `/app/backend/routers/sales_team.py` — deleted
- `/app/frontend/src/components/sales/` (3 components) — deleted
- `users.py`: removed `employment_type` + `manager_id` fields from create/update
- `server.py`: removed sales_team_router import + mount
- `AdminDashboard.jsx`: removed Sales Team sidebar item + render + sales_manager role option + employment_type badge in Users list + employment_type dropdown in user dialog
- `PartnerDashboard.jsx`: removed Team Dashboard conditional sidebar item + sales_manager auth + sales-team render + auto-land
- `AdminHome.jsx`: removed DiscountApprovalInbox
- `PartnerHome.jsx`: removed IncentiveTierWidget
- `Login.jsx`: removed sales_manager route mapping
- DB cleanup: dropped `discount_requests`, `incentive_configs`, `sales_targets` collections; stripped `employment_type`/`manager_id` from users; deleted `salesmgr@leamss.com` user

**Verified**: 404 on `/api/sales-team/*`, clean Users page, existing Admin/Partner/Case Manager/Client flows untouched. Lint clean across modified files.

### In-House Sales Team CRM — Phase 1 + 2 (2026-05-12)

**User-approved P1**: Build foundation + Discount Approval + Tiered Incentive for in-house sales reps. Phase 3 (full Manager Dashboard) next round.

**Phase 1 — Foundation**:
- `users` collection: new `employment_type` field (values: `external` (default) | `employee`) + `manager_id` field
- `PUT /api/users/{id}` accepts both fields with validation
- `POST /api/users` defaults `employment_type=external`
- Admin Users page (AdminDashboard.jsx):
  - New badge column showing 🏢 In-House / 🌍 External next to partner names (data-testid=emp-type-{userId})
  - Edit/Create dialog: new indigo-bordered "Employment Type" dropdown (data-testid=user-employment-type) — appears only when role=partner
  - Explanatory text: "In-house employees get tiered incentives + stricter discount cap (5% vs 10%) and visibility to managers"

**Phase 2 — Discount Approval + Incentive**:
- New router `/app/backend/routers/sales_team.py` mounted at `/api/sales-team` (renamed from `/sales` to avoid existing route conflict)
- Auto-seeded tier config in `incentive_configs` collection:
  - Tiers: Bronze (0-5L @ 5%), Silver (5-15L @ 7%), Gold (15L+ @ 10%)
  - Discount caps: employee 5% auto / 15% manager / 100% admin; external 10% auto / 100% admin
- `POST /api/sales-team/discount-requests` — auto-routes based on % + employment_type. Returns `auto_approved=true` if within cap, else `status=pending` with `level_required`
- `GET /api/sales-team/discount-requests?status=` — admin/manager see all, partner/rep see own
- `POST /api/sales-team/discount-requests/{id}/decide` — approve/reject with optional note; managers blocked from admin-level requests
- `GET /api/sales-team/my-incentive?month=YYYY-MM` — employee-only; aggregates current rep's revenue from closed deals (`proposal_paid` / `awaiting_final_approval` / `case_created` stages), returns current tier + base_payout + next_tier + delta_needed
- `GET /api/sales-team/team-rollup` — admin sees all employees, sales_manager sees own team (by manager_id)
- `GET /api/sales-team/incentive-config` & `PUT /api/sales-team/incentive-config` — admin can adjust tiers/caps; versioning auto-bumps

**Frontend**:
- `/app/frontend/src/components/sales/IncentiveTierWidget.jsx` — mounted on PartnerHome. Gold-gradient tier banner + revenue/deals/commission stats + progress bar to next tier. **Auto-hides for externals** (403 response).
- `/app/frontend/src/components/sales/DiscountApprovalInbox.jsx` — mounted on AdminHome. Pending requests with level badge (auto/manager/admin), employment_type tag, base→discount→final breakdown, optional decision note, Approve/Reject buttons.

**Verified via curl + screenshots**:
- 3% discount → auto_approved instantly (within 5% cap)
- 10% discount → pending, level_required='manager'
- 25% discount → pending, level_required='admin'
- Approve flow works, status updates correctly
- Incentive: ₹2.98L revenue → Bronze tier → ₹14,948 payout, ₹2.01L to Silver visible
- External 403 on incentive endpoint (correct gate)
- Team rollup returns 1 employee rep with revenue + tier
- Frontend: badges render, incentive widget shows on PartnerHome, discount inbox shows on AdminHome

### Active Share Links Dashboard (2026-05-12)

**User-approved potential improvement** following smart-link + expiry control. Compliance + security gold-tier feature.

**Backend**:
- New router `/app/backend/routers/share_links_dashboard.py` mounted at `/api/share-links`
- `GET /api/share-links/?status=&link_type=&search=` (admin only) — unified list of all share-tokens + magic-tokens across all PAs with metadata: issuer, purpose, amount_label, issued_at, expires_at, status (active/expired/revoked/consumed/deactivated), access_count, last_accessed_at/ip/ua, and a `suspicious` flag (heuristic: clicks≥5 while still active)
- `POST /api/share-links/revoke` — admin sets `share_active=false` (for public) or `revoked=true` (for magic) with audit fields: revoked_at/by/reason
- Click tracking added to `GET /pre-assess-portal/public/{token}` — auto-increments `share_click_count` and records `share_last_accessed_at/ip/ua` per visit
- Magic links capture `used_ip/used_ua` on consume + check `revoked` flag (returns 410 'Link revoked by admin')

**Frontend**:
- New component `/app/frontend/src/components/ShareLinksDashboard.jsx` — full audit table with stats strip, search, type filter, click-to-revoke flow with reason capture, suspicious badges, color-coded status pills
- Mounted on AdminHome as third bottom widget (`id=share-links-anchor`)
- New Quick Access tile `quick-share-links-anchor` with indigo accent + smooth-scroll to widget

**Verified visually**: 30 links rendered, filter to "active" shows 15, revoke dialog opens cleanly with reason input. Stats update live after revoke (1 → revoked column).

### Smart Share Link + Expiry Control (2026-05-08)

**User-reported issue + enhancement combined**:

**Issue**: WhatsApp / Copy Public Link button always generated ₹5,100 PA-fee link, even on PAs that were already past `proposal_sent` (where client should pay the proposal fee, e.g., ₹1,50,000). User specifically complained that for an `approved + proposal_sent` PA with proposal fee ₹1,50,000, the share link was still showing ₹5,100.

**Enhancement**: Configurable link expiry (1/7/30/90 days or never).

**Backend** — `/app/backend/routers/pre_assess_portal.py`:
- `GenerateLinkRequest` model gains `expires_in_days: Optional[int]` (allowed values: 0, 1, 7, 30, 90)
- `POST /api/pre-assess-portal/generate-public-link` now branches by stage:
  - **BRANCH A** — fee NOT paid → public share-token URL (`/pre-assess/{token}`), `link_type: 'public_pa_fee'`, `amount: 5100`, `amount_label: '₹5,100'`, `purpose: 'pre_assessment_fee'`
  - **BRANCH B1** — fee paid + `proposal_sent` + linked user → magic-link URL (`/magic/{token}`), `link_type: 'magic_portal'`, `amount: pa.proposal_fee`, `purpose: 'proposal_fee_payment'`
  - **BRANCH B2** — `case_created` + linked → `purpose: 'view_portal'`, `amount: 0`
  - **BRANCH B3** — fee paid but no client_user_id → 400 'Client account not linked yet'
- Expiry honored: `expires_in_days=0` → null `expires_at` for public links, 5-year-out for magic links
- Activity log captures `action='share_link_generated'` with `type` + `expires_in_days` metadata

**Frontend** — `/app/frontend/src/components/pa/PaActionBar.jsx` (full rewrite):
- Both **Copy Public Link** and **WhatsApp** buttons now open a unified dialog (`data-testid=share-dialog-{paId}`)
- 5 expiry option pills (`data-testid=expiry-1, expiry-7, expiry-30, expiry-90, expiry-0`)
- Default = 30 days
- Amber warning banner when "Never expire" selected ("Use only for trusted recipients")
- WhatsApp message text adapts by `purpose`: shows ₹1,50,000 for proposal flows, ₹5,100 for new PAs, "View case status" for case_created
- Dialog also shows generated link with copy+open icons after submission

**Verified**: iteration_91.json — Backend **14/14 PASS** · Frontend **100% PASS** · 0 regressions across previous flows.

### Bug Fix + Edit PA Details (2026-05-08)

**User-reported issues**:
1. **🚨 BUG**: "Forward to Admin" throwing `ReferenceError: pas is not defined` — broke 3 critical handlers (forward / send-proposal / submit-final)
2. **📝 GAP**: No way to edit PA contact details (mobile/email/name) after creation — blocked WhatsApp share for PAs created without mobile

**Bug fix**:
- `/app/frontend/src/components/PreAssessmentPipeline.jsx` — state was named `assessments`/`setAssessments`, but 9 lines across 3 handlers (`handleForwardToAdmin`, `handleSendProposal`, `handleSubmitFinal`) used the wrong identifiers `pas`/`setPas`
- All 9 occurrences renamed correctly
- Forward / Proposal / Final flows now work end-to-end without errors

**New: Edit PA Details**:
- `POST → PUT /api/pre-assessment/{pa_id}/details` — `PADetailsUpdate` Pydantic model accepts: client_name, client_email, client_mobile, client_age, education, work_experience, country, service_type, notes
- Authorization: admin (any), partner (own only), case_manager (any), client (forbidden 403)
- Locked when stage = `case_created` (returns 400 — case must be edited from Case page)
- Diff-detection: only changed fields are persisted, returns `{ok: true, no_change: true}` when nothing different
- Auto-syncs `client_name` + `client_mobile` to linked `users` collection (so client login still works)
- Audit trail via `log_activity` with full before/after diff

**Frontend**:
- New `/app/frontend/src/components/pa/PaEditDetailsModal.jsx` — 8 grid fields + notes textarea + amber "case is locked" warning banner
- Pencil icon button (`data-testid=edit-pa-{paId}`) in every PA card row header — sits next to "Preview as Client"
- Modal applies optimistic UI update (assessment list refreshes immediately on save)

**Tested**: iteration_90.json — Backend **11/11 PASS** (1 skipped: no proposal_paid PA available) · Frontend **100% PASS** · 0 regressions across send-proposal / submit-final / forward / WhatsApp flows. `retest_needed:false`.

### Public Lead-Gen + Doc Expiry + WhatsApp Share (2026-05-08)

**4 user-approved features built and tested**:

#### #1 — AI Eligibility Pre-Score (PUBLIC lead magnet)
- New router `/app/backend/routers/eligibility.py`
- `GET /api/eligibility/pathways` — list 8 pathways
- `POST /api/eligibility/score` — public scoring via Claude Sonnet 4.6 across 8 pathways with tier/timeline/strengths/gaps/notes per pathway + top_recommendation + overall_summary
- `GET /api/eligibility/share/{score_id}` — public shareable result
- Lead capture: when `consent_to_contact=true` + email/mobile provided → auto-creates entry in `leads` collection with priority based on top score (>=70 = high)
- New page `/app/frontend/src/pages/EligibilityCheck.jsx` mounted at `/eligibility` route — public, no login required
- 90-second form → loading state → 8 pathway cards with score bars + tier badges + strengths/gaps + share/re-score/compare CTAs

#### #2 — Document Expiry Tracker (admin/partner/client)
- New router `/app/backend/routers/doc_expiry.py`
- `GET /api/doc-expiry/upcoming?horizon_days=120&severity=critical` — list expiring docs across PA + Case docs with role scoping
- `POST /api/doc-expiry/check-now` — idempotent scan that creates notifications for new bucket-crossings (90/60/30/15/7 days)
- `PUT /api/doc-expiry/pa-doc/{doc_id}/expiry` — set/update expiry on PA doc
- Idempotency: `doc_expiry_alerts` collection logs (doc_id, bucket) so same alert never fires twice
- Severity buckets: expired / critical (≤15d) / warning (≤60d) / info (≤90d) / ok
- New `DocExpiryWidget.jsx` mounted on AdminHome with 4 stat cells + Refresh + Send Alerts buttons
- Role scoping: admin/CM see all, partner sees own PAs, client sees own

#### #3 — WhatsApp Smart Share (zero-cost velocity)
- Updated `/app/frontend/src/components/pa/PaActionBar.jsx` — added green-bordered `MessageCircle` button
- `data-testid=whatsapp-share-{paId}` between "Copy Public Link" and "Preview as Client"
- Opens `https://wa.me/{cleanMobile}?text={prefilled}` with auto-built message: client name, partner name, country/service, PA reference, fee amount, secure link, signature
- No Twilio API needed (pure deep link). Toast error if mobile not on file.

#### #8 — Visa Pathway Comparison (PUBLIC + admin-editable)
- New router `/app/backend/routers/visa_compare.py`
- 8 seeded pathways with realistic 2026 fees/timelines (Canada EE/PNP, Australia 189/190, UK SW, Germany Blue Card, USA EB2-NIW, NZ SMC)
- `GET /api/visa-compare/pathways[?country=]` — public list (auto-seeds if empty)
- `GET /api/visa-compare/compare?slugs=` — 2-4 pathways side-by-side
- `PUT /api/visa-compare/pathways/{slug}` — admin edits (yearly fee refresh)
- `POST /api/visa-compare/reseed` — admin reset to defaults
- New page `/app/frontend/src/pages/VisaCompare.jsx` at `/visa-compare` — public, 8 pickable pills (max 4) → side-by-side cards with timeline / total cost / settlement funds / education / work-exp / age / language / benefits / drawbacks / post-arrival jobs

#### Login page — public access tiles
- `/app/frontend/src/pages/Login.jsx` — added 2 gradient tiles below demo creds: `public-eligibility-link` → /eligibility, `public-compare-link` → /visa-compare

**Tested**: iteration_89.json — Backend **18/18 PASS** · Frontend 100% PASS · 0 issues · 0 regressions. `retest_needed:false`.

### PreAssessmentPipeline Refactor — Round 2 (2026-05-07 night)

**User-approved P2 task**: Further break down `PreAssessmentPipeline.jsx` (was 1066 → 1002 after Round 1).

**6 new sub-components extracted** to `/app/frontend/src/components/pa/`:
- `PaProposalForm.jsx` (131 lines) — Send Service Proposal form with promo, discount, upsell bundles, AI generation buttons (Sonnet 4.6 + Opus 4.6 Premium), live breakdown panel
- `PaDocumentsList.jsx` (92 lines) — Client Documents panel with view (inline)/download/delete handlers per file
- `PaFinalSubmitForm.jsx` (64 lines) — Receipt + Agreement upload + Submit-to-Admin form (proposal_paid → awaiting_final_approval transition)
- `PaForwardForm.jsx` (27 lines) — Partner-review remarks form
- `PaStageProgress.jsx` (23 lines) — Bottom horizontal stage indicator with 7 dots
- `PaActionBar.jsx` (23 lines) — Copy Public Link + Preview as Client + dynamic next-action button

**Result**:
- `PreAssessmentPipeline.jsx`: 1066 → **770 lines** (-296, ~28% reduction)
- All data-testids preserved across extracted components
- Cleaned unused lucide imports (IndianRupee, ArrowRight, Download)
- New `/pa/` directory now houses 8 focused sub-components (Pipeline parent + 8 children)

**Tested**: iteration_88.json — Frontend **100% PASS** · Zero regressions across all PA flows (create/expand/proposal/forward/final-submit/agreement). `retest_needed:false`.

### Compliance Report PDF (2026-05-07 night)

**User-approved enhancement** following SHA-256 tamper detection: a stamped PDF audit report for legal/audit officers.

**Backend** — `GET /api/legal-archive/compliance-report.pdf?start_date=&end_date=` (admin-only):
- ReportLab-rendered A4 PDF (~3-5 KB typical, scales linearly with records)
- Sections: Cover (window, generator, totals) → Integrity scan summary (verified/tampered/unverified counts + flagged records list) → Consents table → E-Signatures table → Invoices table → Report-level SHA-256 chain hash binding all record hashes + timestamp + officer ID
- Default window = last 90 days; configurable via query params
- Returns `X-Report-Hash` header with the binding SHA-256 for client display
- Each table includes the per-record SHA-256 hash prefix
- Footer: page numbers + "LEAMSS · Compliance Report · timestamp" on every page
- 403 enforced for non-admin

**Frontend** — `/app/frontend/src/components/LegalArchive.jsx`:
- New "Compliance Report" gradient button in header (data-testid=`compliance-report-btn`) next to Verify Integrity
- Dialog (data-testid=`compliance-report-dialog`) with From/To date pickers (default last 90d), feature description list, Generate button
- On click: streams PDF, opens in new tab, toast shows first 16 chars of report hash for instant verification

**Verified via curl**:
- Admin default → HTTP 200 + valid `%PDF-1.4` magic + 4.3 KB + correct headers
- Admin custom range → HTTP 200 + 3.2 KB
- Partner → HTTP 403 ("Admin only — Legal Archive is restricted to compliance officers")
- Anonymous → HTTP 403

### SHA-256 Tamper Detection + Legal Doc Polish + PA Refactor (2026-05-07 night)

**User asked**: 1️⃣ Re-seed agreement templates so generated UI/PDF matches uploaded DOCX verbatim with proper typography. 2️⃣ Add SHA-256 tamper detection (Task C). 3️⃣ Refactor PreAssessmentPipeline.jsx (Task D).

**Templates re-seeded** (v2): `seed_agreement_templates.py` re-run — Australia Standard, Australia Protection, Canada Express Entry now have verbatim DOCX text with structured `<h1 class=title>`, `<h2>` annexure heads, `<ul>`/`<table class="client-details">`/`<table class="fee-table">`/`<table class="signature-table">`.

**New shared CSS** `/app/frontend/src/components/agreement-doc.css` — legal-document grade typography:
- Serif font stack (Georgia, Times New Roman, Cambria), 13.5px / 1.7 line-height, justified paragraphs
- Centered title with double-rule underline, italic meta line
- H2 sections with teal left-rule and uppercase tracking; H3 with underline
- Client-details + fee-table with bordered cells, teal header on fee-table, zebra striping
- Signature-table at bottom with 28px sign-line + uppercase muted labels
- A4-feel wrapper `.agreement-doc-wrap` with subtle shadow + light grey backdrop
- Print-friendly media query

Applied via `agreement-doc-wrap` to:
- `AgreementViewerModal.jsx` (admin/partner read-only view)
- `ClientAgreementSigning.jsx` (client scroll-to-sign view)
- `AgreementGenerator.jsx` (partner step-3 preview)
- `AgreementTemplatesManager.jsx` (admin preview)

**SHA-256 Tamper Detection (Task C):**
- New module `/app/backend/core/integrity.py` with `compute_hash`, `verify_hash`, canonical PROJECTIONS per record_type (consent / signature / invoice). Hash = sha256(canonical-JSON of immutable fields).
- All 3 insert sites now persist `integrity_hash` at write-time:
  - `routers/proposal_docs.py` — invoice send + e-sign save
  - `routers/pre_assess_portal.py` — proposal-consent submit
- New endpoints in `routers/legal_archive.py`:
  - `POST /api/legal-archive/integrity/backfill` — adds hash to legacy records (admin-only)
  - `GET /api/legal-archive/integrity/verify-all` — recomputes + diffs all records, returns `{verified, tampered, unverified, tampered_records[]}` 
- `/api/legal-archive/search` now returns `integrity_status` + `integrity_hash` (12-char prefix) per item
- LegalArchive UI: "Verify Integrity" button in header, auto-fires on mount, banner shows verify/tamper counts with red-pulse alert + tampered records list. Each row gets a colored Integrity badge (green ShieldCheck for verified, red ShieldAlert pulse for tampered, slate Shield for legacy/unverified). Backfill button appears only when legacy records present.
- Tamper sanity verified: mutating `body_snapshot.final_amount` directly in Mongo → verify-all flagged 1 tampered record with expected vs actual hash diff. Restored + rehashed.

**Refactor (Task D):**
- Extracted `PaCreateForm` from `PreAssessmentPipeline.jsx` (~75 lines) → `/app/frontend/src/components/pa/PaCreateForm.jsx`
- Trimmed unused lucide imports (User, Mail, Phone, Globe, GraduationCap, Briefcase)
- Pipeline file: 1066 → 1002 lines. All data-testids preserved.

**Tested**: iteration_87.json — Backend **16/16 PASS** · Frontend 100% PASS. 0 issues. `retest_needed:false`.

### Agreement Template Library + Auto-Generator (2026-05-07 PM)

**User uploaded 3 official LEAMSS agreements** (Australia Standard, Australia Protection, Canada Express Entry). Built end-to-end Agreement Template + E-Sign system.

**Backend (`/app/backend/routers/agreement_templates.py`):**
- 2 routers: `agreement_templates_router` + `pa_agreements_router`
- 14 endpoints: list/create/edit/clone/delete/upload-docx/request templates + auto-vars/generate/list/get/sign/pdf for per-PA agreements
- 3-level taxonomy: Country × Visa Category × Policy Variant
- Jinja2 rendering with `{{var}}` placeholders (auto-detected via regex)
- python-docx integration for DOCX upload + HTML extraction
- ReportLab PDF rendering with HTMLParser (preserves headings + bold + paragraphs) + embedded canvas signature image

**Seeded 3 default templates** via `seed_agreement_templates.py`:
- Australia · PR · Standard (5 annexures, INR fees, milestones)
- Australia · PR · Protection (premium variant with 100% refund + free re-application)
- Canada · PR · Express Entry (CICC-registered retainer)

**Frontend components (3 new + 1 enhanced):**
- `AgreementTemplatesManager.jsx` (admin) — CRUD with rich-text editor, placeholder badges, DOCX upload, clone/preview/edit
- `AgreementGenerator.jsx` (partner) — 3-step modal: Select Template → Fill Variables (auto-filled, editable) → Preview & Generate
- `ClientAgreementSigning.jsx` (client) — Full agreement body preview + scroll-to-end gate + canvas signature → green signed card with download
- `AgreementViewerModal.jsx` — read-only view for already-generated agreements with regenerate option
- Enhanced `PaFinancialSummary` — added "Generate Agreement" / "View Agreement" / "Agreement Signed ✓" smart button

**Security:** Admin-only writes for templates. Partner can only generate for own PAs. Client can only sign own agreements (403 enforced at backend).

**Auto-fill placeholders** (29 vars from PA): client_name, client_email, client_phone, client_dob, client_address, client_passport, country, service_type, agreement_date, partner_name, agent_name, pa_number, pre_assessment_fee, proposal_base_fee, proposal_final_amount, promo_code, milestone_1/2/3 amount/date, payment_mode, leamss_agent_email.

**Tested**: iteration_86.json — Backend **24/24 PASS** · Frontend **95% PASS** (1 LOW priority — fixed: View Agreement button now opens dedicated viewer modal instead of generator). `retest_needed:false`.

### Legal Archive (P1) — Admin Compliance Dashboard (2026-05-07 PM)

**User ask**: P1 — Legal Archive tab with searchable consents + signatures + invoices.

**New Backend router** `/app/backend/routers/legal_archive.py` (admin-only):
- `GET /api/legal-archive/stats` — returns `{consents, signatures, invoices, total}`
- `GET /api/legal-archive/search?q=&record_type=&start_date=&end_date=` — unified timeline aggregating from 3 collections (proposal_consent_emails, pa_signatures, pa_invoices). Sorted desc by timestamp, hydrated with PA metadata (client/partner/country).
- `GET /api/legal-archive/{ref_id}` — fetch full record by reference_id
- 403 enforcement helper `_admin_only()` blocks partner/CM/client

**New Frontend component** `/app/frontend/src/components/LegalArchive.jsx`:
- 4 stat cards (Total / Consents / E-Signatures / Invoices) with colored borders
- Free-text search bar (Enter or click Search)
- Filter pills: All / Consents / Signatures / Invoices
- Date range pickers (start/end)
- Results table: Type badge + Reference ID (mono) + Client info + Country/Service + Amount (₹) + Timestamp + Actions
- View Detail modal with type-specific previews:
  - Consent: full fee snapshot (base, promo, custom discount, upsells, final)
  - Signature: IP + file size + UA
  - Invoice: download button
- Inline invoice download icon
- Export CSV button (downloads filtered results)
- Refresh button

**Wired into Admin sidebar** — System group, Shield icon. Partner sidebar excludes it.

**Tested**: iteration_85.json — Backend **17/18 PASS** (1 minor 401-vs-403 ignorable) · Frontend 100% verified · 0 issues. `retest_needed:false`.

### P0 Batch + AI Upgrade (2026-05-07) — Sonnet 4.6 + Opus 4.6 + Optimistic UI

**User asks**: P0 batch (Optimistic UI + Refactor + Lazy-load) + Hybrid AI (Sonnet 4.6 default + Opus 4.6 Premium button).

**AI Model Upgrade ✨**
- Default: `claude-sonnet-4-6` (released Feb 17, 2026 — 30-50% faster than 4.5, same price)
- Premium: `claude-opus-4-6` (deepest reasoning, for ₹5L+ proposals)
- New `premium: bool` field in `AIGenerateRequest`. Response now returns `{model, premium}`.
- Frontend shows TWO buttons in proposal form: ✨ Generate with AI (Sonnet) + 👑 Premium AI (Opus, gradient bg).

**Optimistic UI**
- All stage-changing actions now flip card stage **INSTANTLY** before server confirms:
  - Admin approve/reject (`PreAssessmentQueue.handleReview`)
  - Admin approve-final + create case (`handleApproveFinal`)
  - Partner send-proposal (`handleSendProposal`)
  - Partner forward-to-admin (`handleForwardToAdmin`)
  - Partner submit-final (`handleSubmitFinal`)
- Rollback on failure restores snapshot + toast shows ` — reverted`.

**Refactor**
- Extracted `PaFinancialSummary` (90 lines) into `/app/frontend/src/components/pa/PaFinancialSummary.jsx`. Pipeline file: 1103 → 1037 lines. Same UI / data-testids preserved.

**Lazy-load**
- `DropoffRecoveryWidget` now uses `useRef` + `IntersectionObserver` (rootMargin 100px). Shows "Scroll to load…" placeholder until visible. `/api/intelligence/dropoff-leads` no longer fires on every Home render.

**Tested**: iteration_84.json — Backend **20/20 PASS** · Frontend 100% verified. Zero issues. `retest_needed:false`.

### Performance Fix — Portal Speed + Real-time Notifications (2026-04-23 night)
**User complaint**: "Bahot slow chal raha hai pura portal. Notifications, reviews immediately update nahi ho rahe."

**Root causes found:**
1. **Missing DB indexes** — `pre_assessment_documents.pre_assessment_id`, `activity_log.entity_id`, `notifications (user_id, read, created_at)`, `pa_invoices`, `case_milestones`, etc. all did full-collection scans.
2. **API call explosion** — Expanding one PA card fired 5+ parallel calls (docs + activity + payment-history + risk + checklist).
3. **Stats endpoint serial counts** — 9 sequential `count_documents()` calls per Home page render.
4. **SSE polling 15s** — Felt "not instant" for action notifications.

**Fixes applied:**
- **10 new Mongo indexes** in `core/database.py` (including compound `(partner_id, stage)`, `(user_id, read, created_at)`, `(entity_id, created_at)`, etc.)
- **NEW bundle endpoint** `GET /api/pre-assessment/{pa_id}/bundle` — returns pa + documents + activity + payment_history + checklist + risk in ONE parallel-queried response.
- **Stats endpoint** now uses `asyncio.gather` for all 9 counts in parallel.
- **SSE notification poll** reduced 15s → 5s with UTC-aware datetimes.
- **Frontend components** (`PaymentHistoryTimeline`, `RiskScoreBadge`, `SmartDocChecklist`) now accept `initialData` prop to skip their own fetch when the parent has bundle data.
- **PA expand on Partner Pipeline** uses bundle directly — 1 call instead of 5+.

**Benchmark:**
- Expanding PA card: **701ms → 118ms** (~**6x faster**, 5+ calls → 1 call)
- Stats: serial → parallel (~**9x faster** on large DBs)
- Notifications: max 5s delay instead of 15s (3x more responsive)

### Latest: AI Proposal + Send Proposal 403 Fix (2026-04-23 evening)
**User issue (screenshot)**: Partner clicked "Generate with AI" → red toast "Partners or admins only"; then "Send Proposal to Client" → "Not Authorized". Reproduced via curl: backend worked correctly with fresh partner token, so issue was stale/confusing error message with no status hint.

**Root cause**: Error messages were too generic ("Not authorized", "Partners or admins only") giving no debugging hint about role vs ownership vs stage.

**Fixes applied:**
- `ai_proposal.py`: Now also accepts `case_manager` role. Error explicitly states user's actual role and required roles. Partner-ownership error now says "This pre-assessment belongs to another partner…".
- `pre_assessment.py` send-proposal: Role check and partner-ownership check split with distinct messages. Stage mismatch now says "Pre-assessment is at stage 'X'. Must be at 'approved' stage (after 1st Admin approval)".
- Frontend handleGenerateAI + handleSendProposal: Display HTTP status code + detailed detail. 401 specifically surfaces "Session expired — log in again". console.error for devtools.

**Verified via curl**:
- Partner owner → AI generate 200 (303 words) + send-proposal 200
- Client role → AI generate 403 with crystal-clear message
- Already-sent PA → send-proposal 400 with stage hint

### Phase B + C + D Complete (2026-04-23 PM) — MASSIVE RELEASE

**User ask**: Build Phase B (Proposal PDF + Digital E-Sign + Send Invoice button), Phase C (Payment History + Auto Invoice + Milestone Payments), Phase D (Drop-off Recovery + Smart Doc Checklist + Risk Prediction), plus consent-summary email auto-trigger with Reference ID for legal records. "Sab achese interlink ho — koi link break nah hojayega."

**New Backend routers (all wired in server.py):**
1. `/app/backend/routers/proposal_docs.py` — ReportLab A4 branded PDFs + e-sign
   - `GET /api/proposal-docs/{pa_id}/proposal.pdf` / `invoice.pdf`
   - `POST /api/proposal-docs/{pa_id}/send-invoice` (MOCK email + records Reference ID)
   - `GET /api/proposal-docs/{pa_id}/invoices`
   - `POST /api/proposal-docs/{pa_id}/esign` (client-only, saves PNG + IP + UA)
   - `GET /api/proposal-docs/{pa_id}/esign`
2. `/app/backend/routers/payment_history.py` — two routers
   - `GET /api/payment-history/pa/{pa_id}` + `/case/{case_id}` (unified timeline)
   - `POST /api/milestones/case/{case_id}/create`, `GET /api/milestones/case/{case_id}`
   - `POST /api/milestones/{mid}/mock-pay`, `mark-paid`, `DELETE /api/milestones/{mid}`
3. `/app/backend/routers/intelligence.py` — Phase D
   - `GET /api/intelligence/dropoff-leads` (stage-SLA detection, severity, suggested_action)
   - `POST /api/intelligence/nudge/{pa_id}` (MOCK email + in-app notification)
   - `GET /api/intelligence/checklist/{pa_id}` (4 templates: canada_express_entry, australia_skilled, uk_work_visa, usa_h1b, default)
   - `GET /api/intelligence/risk/{pa_id}` (rule-based 0-100 score using age, education, experience, stage, docs, idle time, rejection history)

**Consent Summary Email (legal paper-trail):**
- Modified `POST /api/pre-assess-portal/client/proposal-consent/{pa_id}` to emit `reference_id` (format: `CON-<PA#>-<YYMMDDHHMM>`), persist full body_snapshot (base_fee + promo + upsells + final_amount + consent_at) in `proposal_consent_emails` collection, notify both client + partner
- New `GET /api/pre-assess-portal/client/consent-summary/{pa_id}` for archived view

**New Frontend components (6):**
- `SignatureCanvas.jsx` — HTML5 canvas drawing + typed-name verification
- `PaymentHistoryTimeline.jsx` — vertical timeline w/ received/pending totals
- `MilestonesManager.jsx` — create/pay/mark-paid/delete milestones (role-aware)
- `RiskScoreBadge.jsx` — risk pill + factor breakdown
- `SmartDocChecklist.jsx` — progress bar + checklist items
- `DropoffRecoveryWidget.jsx` — stuck-leads list with Nudge buttons

**Enhancements to existing:**
- **PartnerHome + AdminHome**: DropoffRecoveryWidget mounted at bottom
- **PreAssessmentPipeline (Partner)**: Financial Summary now has 3 action buttons (Download Proposal PDF · Download Invoice PDF · Send Invoice to Client) + below it a 2-col block with Payment Timeline + Risk Badge + Smart Checklist (when fee_payment_status=paid)
- **PreAssessmentMiniPortal (Client)**: Consent flow shows Reference ID inline + archived summary; new "E-Sign Your Service Agreement" card with SignatureCanvas (proposal_paid stage); "Your Payment Records" card with Proposal/Invoice download + PaymentHistoryTimeline
- **ClientDashboard → My Journey tab**: PaymentHistoryTimeline (case scope) + MilestonesManager for active cases

**Tech additions:**
- ReportLab (already installed v4.4.10) — A4 branded PDFs with logo, parties, fee breakdown table, consent clause, footer
- New collections: `pa_signatures`, `pa_invoices`, `proposal_consent_emails`, `case_milestones`, `pa_nudges`

**Tested**: iteration_83.json — Backend **49/49 PASS** · Frontend 100% · 0 regressions on Phase A · 0 issues. `retest_needed:false`.

### Latest: 3 Document UX Fixes (2026-04-23)
**User feedback**: "Document View download ho raha hai instead of inline open. Partner upload ke liye explicit Upload button chahiye aur Delete option bhi. Awaiting Final Approval stage pe Financial Summary dikhao."

**All 3 fixed:**
1. **Inline View** — Backend `GET /api/pre-assessment/{pa_id}/document/{doc_id}/download?inline=true` sets `Content-Disposition: inline` (via FileResponse `content_disposition_type`). Both Partner Pipeline + Admin Queue View buttons fetch with `?inline=true`, create blob URL, open in new tab. Save/Download buttons omit param (defaults to `attachment`).
2. **Explicit Upload flow** — Replaced auto-upload-on-select with 2-step staging: `pendingUpload[paId] = { file, docType }`. Selecting a file now shows filename + size + doc-type preview with explicit **Upload** + **Cancel** buttons. Applied to both `payment_received` zone + final-submit zone. data-testids: `file-input-{paId}`, `upload-btn-{paId}`, `cancel-upload-{paId}`, `final-upload-btn-{paId}`, `final-cancel-upload-{paId}`.
3. **Delete docs** — `DELETE /api/pre-assessment/{pa_id}/document/{doc_id}` (allowed for doc-owner client, PA's partner, admin). Frontend XCircle button with window.confirm. data-testid: `delete-doc-{docId}`.
4. **Financial Summary block** — NEW emerald gradient card visible at `proposal_paid`, `awaiting_final_approval`, `case_created` stages. Shows PA Fee ₹5,100 + Main Service breakdown (Base Fee, Promo discount with code, Custom Discount, Upsells list+total, Final Paid) + Total Received badge + Proposal notes.
5. **Awaiting Final Approval banner** — NEW indigo waiting banner at `awaiting_final_approval` stage with Hinglish subtext "Aapka role iske baad complete ho jayega".

**Tested**: iteration_82.json — Backend 29/29 PASSED, Frontend 100% verified. 0 issues. `retest_needed: false`.

## Complete Feature List (2026-04-15 to 2026-04-17)

1. **Step-wise Document Management** - Admin/CM/Client document flow
2. **Unified Client Document View** - Single "Documents & Steps" tab
3. **Smart Template AI** - 8 verified templates, 51 countries
4. **AI Workflow Builder** - Country->Visa->Generate->Edit->Save with SVG flags
5. **Government Forms** - 48 official forms (7 countries) with download links
6. **AI Verification System** - Admin verifies AI data before saving
7. **Deadline & SLA Tracker** - Auto document expiry, manual deadlines, color-coded urgency
8. **Client Intake Form Builder** - Product-specific, role-based (Client/CM/Both), Admin-managed
9. **Automated Government Fee Calculator** (2026-04-17) - 20 countries, live INR conversion

### Latest: 5 Critical UX Fixes (2026-04-22 late night)
**User-reported issues:**
1. Partner + Admin couldn't View/Download client-uploaded documents
2. Admin 1st Approval tab didn't show approved/rejected history (only pending)
3. Partner cards at `proposal_sent` stage had no "Waiting for Client Payment" visual cue
4. Client saw blind "Pay" button without full proposal details + breakdown + consent
5. After client pays, case went straight to admin — partner couldn't upload receipt/agreement/docs first

**All 5 fixed:**
- **Doc View/Download**: NEW `GET /api/pre-assessment/{pa_id}/document/{doc_id}/download` endpoint. Partner + Admin cards show "View" (opens new tab) + "Save" (download) buttons per doc.
- **1st Approval history**: Admin's 1st Approval filter now includes approved/rejected/proposal_sent/etc items (visible history)
- **Waiting banner**: `proposal_sent` cards now show pulsing amber "Waiting for Client Payment" banner with client name + fee amount. Stage label renamed "Waiting for Client Payment".
- **Rich proposal + consent**: Client MiniPortal at `proposal_sent` now shows (a) AI proposal text, (b) Pricing breakdown (base, promo, discount, upsells), (c) Partner note, (d) mandatory consent checkbox with SLA + no-misleading-info language, (e) "I Agree — Unlock Payment" gate button, (f) only after consent → Pay button unlocked. Backend enforces: `mock-pay-proposal` returns 400 if `proposal_consent_given` false.
- **NEW stage `awaiting_final_approval`**: Inserted between `proposal_paid` and `case_created`. Flow: Client pays → partner notified → partner uploads payment receipt + signed agreement + basic docs → Partner "Submit to Admin for Final Approval" → stage becomes `awaiting_final_approval` → admin queue shows it → admin activates case + assigns CM.

**NEW endpoints:**
- `GET /api/pre-assessment/{pa_id}/document/{doc_id}/download` (all roles)
- `POST /api/pre-assess-portal/client/proposal-consent/{pa_id}` (client-only)
- `POST /api/pre-assess-portal/partner/submit-final/{pa_id}` (partner/admin)

**Tested**: iteration_81.json — 28/28 backend + frontend 90%+ verified. 0 issues.

### Deep-Link Filtering + Fresh DB (2026-04-22 night)
**User feedback**: "Admin Home mein '1st Approval' click kiya tho pura Pre-Assessments tab open ho raha — sirf wohi cases dikhne chahiye. Plus saare test data delete karo, fresh se test karunga."

**Solution 1 — DB Cleanup**:
- Created `/app/backend/cleanup_test_data.py` — deleted 1,315 records across 13 collections
- Preserved: 6 seeded users, products, workflows, fee_database, promo_codes, upsell_bundles

**Solution 2 — Deep-link filtering**:
- `PreAssessmentQueue` + `PreAssessmentPipeline` now accept `initialFilter` prop
- Admin/Partner action cards pass filter → opens filtered view only
- Amber context banner + Clear-filter button when filter active
- Stats cards clickable for instant filtering
- Filter auto-clears on sidebar click

**Tested**: iteration_80.json — 14/14 backend + frontend 100%, 0 issues.

### Dashboard UX Simplification + AI → Claude (2026-04-22 PM)
**Problem solved**: User was overwhelmed with 20+ tabs in Admin, 8+ in Partner — "itna complicated kyu bana hai?"

**Solution**: Action-first redesign WITHOUT deleting any feature
- **NEW `PartnerHome.jsx`**: Home tab showing greeting + 4 pulsing action cards (partner_review / approved / new_leads / proposal_paid) + Quick access tiles + Recent PAs list
- **NEW `AdminHome.jsx`**: Home tab showing greeting + 3 approval cards (1st approval, 2nd approval, unassigned cases) + Org snapshot + Quick access grid
- **NEW `FunnelProgress.jsx`**: Reusable 5-step pipeline indicator (Created → Admin Approved → Proposal Sent → Main Fee Paid → Case Active) — inserted at top of every expanded PA card

**Sidebar regroup (no deletions)**:
- Partner: `Home` → `Daily Work` (PA, Leads, Tickets) / `Sales & Earnings` (Sales, Commission, Performance) / `Tools` (Fee Calc, Classic Dashboard)
- Admin: `Home` + `Classic Dashboard` as first 2 items, all other 20+ tabs retained in existing groups
- All previously-accessible tabs still navigable

**AI switch**: GPT-5.2 → **Claude Sonnet 4.5** (`claude-sonnet-4-5-20250929` via Emergent LLM key)
- Better warmth + immigration-domain empathy in proposal writing
- Model changes in `/app/backend/routers/ai_proposal.py` lines 109 + 130

**Tested**: iteration_79.json — 17/17 backend + frontend 100%, **0 regressions on any existing tab**. All user feature guarantees honoured.

### Phase A Retouch + 3 Major Features (2026-04-22)
**🔧 Critical Flow Fixes:**
- **NEW stage `partner_review`** — Between client-submit and admin-queue. Client submit → Partner gets "Action needed" notification + pink pulsing badge → Partner reviews in expanded card → Partner forwards with remarks → Admin queue
- **Partner card visibility** — Expanded card now shows 2 panels: "Client Documents" (file list + type badge) + "Client Activity" (timeline). Auto-loads on expand.
- **Strict Sales Rule** — `POST /sales` now rejects partner-created sales that lack `pre_assessment_id` UNLESS `bypass_pre_assessment=true` with `bypass_reason` (min 10 chars). Admin/CM unaffected.
- **Partner role extended** — Partner remains active through stages: new → partner_review → approved → proposal_sent → proposal_paid → **case_created (role ends here after CM assigned)**

**✨ Smart Discount Engine (wired):**
- Existing `/api/marketing/promo` CRUD + validate already backed
- Now integrated into Send Proposal form: promo code input + Apply btn + live discount preview
- `send-proposal` backend validates promo, increments `current_uses`, stores `promo_code`, `promo_discount_amount`, `total_discount_amount` in sale + PA

**📦 Upsell Bundles (new):**
- New `/api/upsell-bundles` CRUD + `/resolve` endpoint
- Auto-seeds 6 default bundles: Priority Processing ₹5k, Family Member +₹15k, Doc Courier ₹3.5k, Extended Consultation ₹8k, Mock Interview ₹4.5k, Landing Package ₹12k
- Admin UI: `UpsellBundlesManager.jsx` under Planning Tools (create/edit/delete)
- Partner UI: Checkbox grid in Proposal form; selected bundles auto-add to `upsell_total`

**✨ AI Proposal Generator (new):**
- New `/api/ai-proposal/generate` — uses **GPT-5.2** via Emergent LLM key
- Reads client profile (name, country, visa, age, education, experience, partner notes) + generates 250-380 word professional proposal body
- Tone options: professional | friendly | assertive
- Partner UI: "✨ Generate with AI" button in proposal form → auto-fills editable textarea

**📊 Enhanced Proposal Form breakdown:**
```
Base Fee:            ₹1,50,000
Promo (SAVE10 10%):  -₹15,000
Custom Discount:      -₹5,000
Upsells (2):         +₹8,000
─────────────────────────
Final Amount:        ₹1,38,000
```

**Tested**: 100% (15/15 backend + frontend all green) — iteration_78.json, 0 issues

### Latest: Pre-Assessment Client Portal Layer — Phase A Part 3 (2026-04-17)
- **Full E2E CRM sales funnel LIVE (MOCK payments)**: Partner creates PA → Client pays via public link → Magic-login → Upload docs → Submit for review → Partner validates & forwards → Admin 1st approval → Partner sends proposal → Client accepts + pays main fee → Admin 2nd approval assigns CM → Real Case created & active
- **NEW Admin endpoints**:
  - `GET /api/pre-assess-portal/admin/case-managers` — lists active case managers for the Assign-CM dropdown
  - `POST /api/pre-assess-portal/admin/approve-final/{pa_id}` — now accepts `{case_manager_id}` body, validates CM, attaches to new case, notifies CM
- **NEW Partner endpoint**: `POST /api/pre-assess-portal/partner/preview-magic/{pa_id}` — short-lived (30min) magic link so partner can preview exactly what client sees in MiniPortal
- **Admin UI enhancements** (`PreAssessmentQueue.jsx`):
  - 6-card stats grid (Total, 1st Review, Approved, Rejected, Awaiting Case, Conversion)
  - `proposal_paid` items now appear in admin queue with orange "Create Case" CTA
  - 2nd-approval UI with **Case Manager dropdown** (optional assign-or-later)
  - Admin sidebar: new "Pre-Assessments" menu item under Cases & Users
- **Partner UI enhancements** (`PreAssessmentPipeline.jsx`):
  - "Copy Public Link" + "Preview as Client" buttons now visible on **every** PA card (all stages)
  - Preview as Client button also in card header for 1-click access
  - Copy Link now returns **full URL** (`window.location.origin` + path) — shareable via WhatsApp/email
- **Admin queue backend updated** to include `proposal_paid` stage in `/api/pre-assessment/admin/queue`
- **Tested**: 100% (10/10 backend + frontend all green) — iteration_76.json + iteration_77.json

### Pre-Assessment Client Portal Layer — Phase A Part 2 (2026-04-17)
- **Client MiniPortal** (`/app/frontend/src/components/PreAssessmentMiniPortal.jsx`): Beautiful stage-aware dashboard shown to clients who have a pre-assessment but no active case
  - 6-step progress pipeline (Paid → Upload → Review → Approved → Proposal → Case Active)
  - Stage-specific UI: `payment_received` shows upload UI + Submit button; `documents_submitted/under_review` shows "Under Review"; `approved` shows "Congratulations"; `proposal_sent` shows Accept + Pay buttons; `proposal_paid` shows "Activating your case"; `rejected` shows refund notice
- **Dynamic Sidebar** (`ClientDashboard.jsx`): When `isMiniMode=true` shrinks sidebar to Overview + Tools (AI Scanner only, +Cost Estimator & Eligibility in `isExpandedMode`) + Communication + Profile
- **New Backend Endpoints**:
  - `POST /api/pre-assess-portal/client/submit/{pa_id}` — client marks docs as ready, stage → documents_submitted, notifies partner
  - `POST /api/pre-assess-portal/client/accept-proposal/{pa_id}` — client accepts partner's proposal
  - `POST /api/pre-assess-portal/client/mock-pay-proposal/{pa_id}` — MOCK main-fee payment, stage → proposal_paid
  - `POST /api/pre-assess-portal/admin/approve-final/{pa_id}` — admin's 2nd approval: creates real Case record + copies workflow steps, stage → case_created
- **Updated**: `GET /client/portal-access/{pa_id}` now returns `can_submit_for_review` flag; mini access_level now covers rejected/refund stages
- **Tested**: 100% (11/11 backend tests) — iteration_75.json; Frontend UI verified for multiple stages

### Pre-Assessment Client Portal Layer — Phase A Part 1 (2026-04-17)
- **New router**: `/app/backend/routers/pre_assess_portal.py` extends existing `pre_assessments` collection
- **Public endpoints (no auth)**: `GET /public/{token}`, `POST /public/mock-pay` — creates client user + magic link
- **Magic login** (72h token) + **OTP fallback** (email/phone, 10-min code)
- **Client endpoints**: `my-assessments`, `portal-access/{pa_id}` (returns mini/expanded/full access level)
- **Activity log**: `activity/log`, `activity/pa/{pa_id}` — partner visibility
- **Public pages** (`/pre-assess/:token`, `/magic/:token`): premium branded payment + login UI
- **Verified E2E**: Partner creates PA → generates public link → unauthenticated client pays (MOCK) → user auto-created → magic link issued → client logs in → fetches own assessments → `access_level: mini` + `can_upload_docs: true`

### Previous: AI Document Scanner (P1 Feature)
- **Backend**: `/app/backend/routers/doc_extraction.py` — GPT-4o Vision via Emergent LLM Key
- **Supported docs**: passport, visa, educational cert, academic transcript, IELTS, bank statement, PCC, marriage/birth cert, driver license, offer letter + auto-detect
- **Endpoints**: `/doc-types`, `/sample-docs` (public), `/sample-docs/{id}/extraction` (public demo), `/extract` (base64), `/extract-upload` (multipart), `/save`, `/history`
- **5 pre-loaded specimen docs** with pre-computed extraction (no API cost for demo)
- **Frontend**: `DocumentExtractor.jsx` with 2 tabs (Upload & Extract + Try Demo), animated extraction progress, field-by-field confidence bars (green/amber/red), AI Verified badges, editable fields, Save to Records
- **Integrated in**: Client Dashboard (Tools → AI Document Scanner) + CM Dashboard (Tools)
- **Verified**: 95% confidence on real test_passport.jpg extraction with correct fields (Patel, Anil Kumar, Z9876543, ISO dates)
- **Tested**: 100% (25/25 backend tests passed) — iteration_74.json

### Previous: Fee Database CRUD + Per-Estimate Edits (v3)
- **Option B — Master Fee Database Editor** (Admin-only):
  - Migrated hardcoded `FEE_DATABASE` dict → MongoDB collection `fee_country_catalog` (auto-seeded on first run)
  - 7 new CRUD endpoints: `admin/catalog`, `admin/countries` (POST/PUT/DELETE), `admin/countries/{id}/categories` (POST/PUT/DELETE), `admin/reseed`
  - Full UI `FeeDatabaseManager.jsx` — Admin Sidebar → Planning Tools → Fee Database
  - Add unlimited new countries (slug auto from name) + categories + fee line items (label, amount, mandatory, per_applicant, notes)
  - Reseed utility to revert to built-in defaults
- **Option A — Per-Estimate Inline Edit**:
  - `CalculateRequest` supports `overrides` (correct fees per estimate) + `extra_lines` (ad-hoc custom charges)
  - UI: pencil icon on each fee line → inline editor for label/amount/notes → "Edited" / "Custom" badges
  - "Add Custom Line" button + "Reset all edits" revert button
  - Overrides are per-estimate (don't touch master catalog)
- **Tested**: 100% (25/25 backend) — iteration_73.json; minor 404 issue fixed post-test

### Previous: Share Estimate Link (v2)
- **5 new endpoints**: `share/{id}`, `share/{id}/deactivate`, `share/{id}/stats`, public `public/{token}`, public `public/{token}/lead`
- **Public URL**: `/shared-estimate/:token` — no login, branded view with breakdown + lead capture CTA
- **View count tracking** (per-view increment on public access)
- **Lead capture** auto-assigns lead to estimate owner with source='shared_fee_estimate', priority='high', tag='fee-estimate-viewer' + sends notification
- **Auto-expiry** (default 30 days, max 365) with 410 Gone response when expired
- **Deactivate** kill-switch for owner/admin
- **Tested**: 100% (25/25 backend) — iteration_72.json
- **UI in FeeCalculator**: Share button → dialog shows link + copy + view/lead/expiry stats + deactivate
- **New page**: `/app/frontend/src/pages/SharedEstimate.jsx` with premium branded layout, lead form, success state

### Previous Feature: Automated Government Fee Calculator (v1)
- **Backend**: `/api/fee-calculator/*` (7 endpoints) in `routers/fee_calculator.py`
- **Countries**: 20 (Canada, Australia, UK, USA, NZ, Germany, Singapore, UAE, Ireland, France, Netherlands, Portugal, Spain, Japan, South Korea, Sweden, Denmark, Switzerland, Hong Kong, Malaysia)
- **Currencies**: USD/CAD/AUD/GBP/EUR/NZD/SGD/JPY/SEK/DKK/CHF/HKD/MYR/KRW/AED + INR
- **Live FX**: frankfurter.dev (ECB) cached 1 hr + static fallback
- **Real 2025-26 official fees**: application, biometrics, medicals, skills assessments, language tests, priority surcharges
- **Line items support**: mandatory vs optional, per-applicant multiplier, official_url links, notes
- **Consultancy service fee + GST** (only shown for Partner/CM/Admin; hidden for Clients)
- **Output**: Dual-currency display (Native + ₹INR), Copy-to-Clipboard, Print/PDF, Attach-to-Case
- **Collection**: `fee_estimates` (saved for proposals/cases)
- **Frontend**: `FeeCalculator.jsx` reusable component
- **Integrated in**: Partner (Fee Calculator tab), Case Manager (Tools), Client (Cost Estimator), Admin (Tools)
- **Tested**: 100% backend (28/28 pass in iteration_71)

## Test Credentials
- Admin: admin@leamss.com / Admin@123
- CM: manager@leamss.com / Manager@123
- Partner: partner@leamss.com / Partner@123
- Client: client@leamss.com / Client@123

## Roadmap / Pending

### Next (User-approved)
- **P1**: Improved Document Info Extraction UI + Demo Mode (live OCR-style extraction preview, sample demo, field-level confidence scores, AI verified badges)
- **P1**: White-Label SaaS Multi-Tenancy Architecture (`agency_id` on all core collections, tenant context in JWT, Super-Admin portal, branding, commission mgmt)

### Backlog
- P2: Resend Email live dispatch (requires user RESEND_API_KEY)
- P3: Twilio WhatsApp full integration
- P3: Comparison Tools (on hold, user to specify approach)

### Backend Routers
ai_workflow_builder, deadlines, intake_forms, step_documents, fee_calculator + core (auth, cases, documents, payments, etc.)
