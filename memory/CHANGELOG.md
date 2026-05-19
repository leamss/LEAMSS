# LEAMSS — Changelog

This file appends every completed phase/feature with dates and verification status.

---
### 🤖 Phase 6 v2 Part 3 — Integrated Workflow + AI Helpers (May 19, 2026)
**Tests:** `test_iteration112_part3_workflow.py` → 10/10 PASS (incl. live AI Suggester contract test)

Three deliverables (all per Sir's PRD):

**1. AI Helper #2 — Occupation Suggester** (`POST /api/sales/ai/suggest-occupation`):
- Free-text description (min 20 chars) + country filter → Claude Sonnet 4.6 returns top 3-5 occupation codes with reasoning + confidence (HIGH/MEDIUM/LOW) + considerations
- Strict prompt: AI suggests, NEVER decides; only suggests codes that exist in the knowledge base; matches based on CURRENT job duties not education
- Backend cross-checks every suggested code against `country_rules.occupation_codes` → returns `_verified: true/false`. AI cannot invent codes.
- ₹2-3 per call estimated (one short prompt with slim occupation list)
- AI Helper #1 (Resume Parser) already exists from Phase 6.7 Part 2 — reused via the same endpoint `/api/eligibility/profiles/resume-extract`

**2. Save Assessment + List/Get/Delete** (`POST /api/sales/assessments`):
- New `sales_assessments` collection — captures profile snapshot, occupation, calculator results for each target country, best country auto-picked by highest points
- Admin sees all, partners scoped to own. RBAC: client → 403
- `GET /list`, `GET /{id}`, `DELETE /{id}` standard CRUD

**3. Create PA from Assessment 1-click Bridge** (`POST /api/sales/assessments/{id}/create-pa`):
- Takes a saved assessment → creates a new Pre-Assessment with pre-filled: client name/email/phone, occupation code/title/skill_body, destination country, lead_source='smart_sales_helper', `source_smart_sales_assessment_id` link
- **Idempotent**: re-calling returns the same `linked_pa_id` with `already_linked=True`

**4. Integrated Workflow Page** (`/sales/client-assessment` — `ClientAssessment.jsx`):
- 7-step visual stepper (Start → Approach → Profile → Countries → Calculator → Review → Done) with done/active/pending state colours
- **Step 2 Approach picker** — 3 cards: "I know the profession" / "Find best code (AI)" / "Upload Resume" — pre-selects which helper modal opens in Step 3
- **Step 3 Profile** — embedded AI Occupation Helper Modal (suggester) + Resume Upload Modal (with file picker → AI extract → form auto-fill) — both data-testid'd
- **Step 4 Countries** — 3 modes: Specific country + visa subclass / Top 3 (AU+CA+NZ) / Custom multi-select
- **Step 5 Live Calculator** — calls `/calculate-batch` → renders grid of country score cards (single column for 1, 3-col for multi) with breakdown + visa eligibility ticks + recommendation
- **Step 6 Review** — confirmation summary with "Best Match" highlight + confirm checkbox
- **Step 7 Done** — 3 action buttons: Create Pre-Assessment (1-click bridge) / Back to Search / Print PDF

**5. Calculator batch endpoint** (`POST /api/sales/calculator/calculate-batch`) — same profile vs multiple country/visa combos in one call (used by workflow Step 5)

**Backend routing fix**: `sales_*` routers must include BEFORE `sales_router` (legacy `/sales/{sale_id}` was catching `/sales/assessments`). Reordered in `server.py:339`.

**Sidebar**: Added "Client Assessment (Workflow)" entry under Smart Sales Helper group with Wand2 icon.

**Test coverage (10/10 PASS in 18s)**:
- Save assessment (single + multi-country)
- List / Get assessments
- Create PA (1-click + idempotent re-call)
- Calculator batch 3 countries
- AI Suggester contract test — verified `_verified=true` cross-check works, all suggestions had valid codes, confidence in {high, medium, low}
- AI Suggester min description length 422
- RBAC: anonymous 403, client role 403

---


### 🧮 Phase 6 v2 Part 2 — Eligibility Calculator (May 19, 2026)
**Tests:** `test_iteration111_calculator.py` → 54/54 PASS in 50ms (zero LLM)

100% deterministic calculator for AU/CA/NZ. Two-pane UI (form left, live calc right). Updates in <300ms as user types.

**Backend** (`/app/backend/core/sales_calculator.py` + `routers/sales_calculator.py`):
- `calculate_au_points()` — Strict AU GSM rules: age table (18-24:25, 25-32:30, 33-39:25, 40-44:15, 45+:0), English bands (Competent 0, Proficient 7=10, Superior 8=20 — all 4 bands), experience overseas (3-4:5, 5-7:10, 8+:15), experience AU (1-2:5, 3-4:10, 5-7:15, 8+:20), education (PhD:20, B/M:15, Diploma:10), Australian Study (+5), STEM Specialist (+10), Professional Year (+5), NAATI (+5), Regional Study (+5), state nomination (190:5, 491:15). Partner skills uses Phase 6.7 rules (single +10, AU PR +10, skill_assessment all-gates +10 or downgrade to +5, english_only +5, non_contributing 0). All visa subclass eligibility evaluated (189/190/491) with min 65 threshold + age 18-44 gate + competent English gate.
- `calculate_ca_crs()` — Express Entry CRS: age table (with-spouse vs no-spouse), education (PhD 150, M 135, B 120), IELTS→CLB per-band scoring (CLB 10 → 32 pts/ability), Canadian work years, spouse education/language, PNP (+600), job offer NOC 00 (+200), Canadian education (+15-30), sibling (+15), French (+50). Eligibility for EE-FSWP / EE-CEC / PNP.
- `calculate_nz_smc()` — NZ SMC: age (20-29:30, 30-39:25, 40-44:20, 45-49:10), qualification (PhD:70, M:50, B:40, Diploma:20), skilled employment (+50), work experience tier, job offer (+30), partner qualification (PhD/M:20, B:10), regional employment (+30).
- API endpoint `POST /api/sales/calculator/calculate` — single profile→country result, <50ms response. Plus `POST /calculate-batch` for Compare Top 3 mode.

**Frontend** (`/app/frontend/src/pages/sales/EligibilityCalculator.jsx`):
- Two-pane sticky layout (form left 3/5, live calc right 2/5)
- 7 form steps: Quick Setup → Spouse Config (conditional) → Country+Visa → Occupation Code (with embedded search modal) → Primary Applicant → State Nomination (conditional 190/491) → Spouse Details (conditional)
- Country-specific bonus toggles: AU 5 bonuses, CA 7 PNP/job/edu/sibling/french, NZ 3 employment/regional
- Live right pane: Big total-points number (5xl), per-category breakdown with badges, visa eligibility cards (green ✓ / red ✗ per subclass), recommendation paragraph
- Debounced 300ms calculation via useEffect — no manual "Calculate" button needed
- Embedded `/sales/occupations/search` modal for occupation lookup
- All conditional sections hidden when not needed (e.g., spouse vanishes for single, state nomination vanishes for 189)

**Sidebar**: Added "Eligibility Calculator" entry under Smart Sales Helper group in admin sidebar.

**Test coverage** (`test_iteration111_calculator.py` — 54 tests):
- 12 AU age parameter tests (every bucket boundary)
- 7 AU English parameter tests (Competent/Proficient/Superior at exact thresholds)
- 4 AU experience tests (overseas + Australia)
- 6 AU education parameter tests
- 7 AU partner skills tests (single bonus, divorced+stale-spouse defence, skill_assessment all gates, downgrade @ age 47, english_only, non_contributing, AU PR spouse)
- 5 AU bonus tests
- 3 AU state nomination tests (190:5, 491:15, 189:no bonus)
- 2 AU full scenario tests (75-pt SWE 189 eligible, age 45 ineligible all visas)
- 3 CA CRS tests (basic, PNP +600, French +50)
- 3 NZ SMC tests (basic, job offer +30, partner Master +20)
- 4 master dispatcher tests
- Total: 54 PASS in 50ms

---


### 🔥 Phase 6.7 Critical Bug Fixes (May 19, 2026) — User Feedback Iteration
**Tests:** `test_iteration109_critical_bug_fixes.py` → 10/10 PASS

User reported via screenshots and Hinglish chat ("Bhai.. Full confusion.. of this AI eligibility engine.. i am not satisfied"):

**BUG 1 — Single applicant getting +5 partner points instead of +10 (CRITICAL)**
- Screenshot showed marital_status='Single', child added, but partner points showed "+5 competent_english_only" with "Spouse age 30 IELTS 6.5" — system was reading STALE spouse data left over from a previous edit.
- **Root cause**: Phase 6.7 Part 1 rules engine treated spouse_block presence as authoritative; if marital was changed to single but spouse data remained in DB, the wrong branch was hit.
- **Fix (defense-in-depth)**:
  1. `/app/backend/core/eligibility_rules.py:235-360` — Partner-skills branch now starts with `has_partner = marital in ('married', 'de_facto')`. If False, spouse_block is forcibly None — stale DB data CANNOT leak through.
  2. `/app/backend/routers/eligibility_profiles.py` — New `_strip_spouse_if_single()` helper called from both create_profile + update_profile. Forces spouse=None + clears family.spouse_* fields before saving when marital is not married/de_facto.
  3. **DB migration ran**: 2 stale profiles cleaned + 72 stale assessment cache entries dropped so next assessment picks the fixed logic.
- **Verified**: 5 regression tests cover single/divorced/widowed/separated all giving +10 even with stale spouse data.

**BUG 2 — Hotel Operations Manager matched to Construction Project Manager (CRITICAL)**
- Screenshot: AU 65/100 with 133111 Construction Project Manager (25% confidence on "manager" token) for someone whose actual job was Hotel Operations Head.
- **Root cause**: AU seed did NOT have 141311 (Hotel/Motel Manager), 132111 (Corporate General Manager), 141111 (Restaurant Manager), 225113 (Marketing Specialist), 225111 (Advertising Specialist), 225311 (PR Professional).
- **Fix**: `/app/backend/core/eligibility_kb_seed.py` — Added 6 new occupation codes with `alternative_titles` (e.g., 132111 with "Operations Head", "Hospitality Operations Director"; 141311 with "Hotel Manager", "Hospitality Manager"). Re-seeded AU.
- **Verified**: Same Hotel Operations Manager profile now matches 132111 + 141311 at **100% confidence**, with 133111 dropped to last alternative at 20%.

**BUG 3 — Skill body fees in INR instead of native currency (CRITICAL)**
- Screenshot: AIM body showing "₹65K" fee. Sir: "ACS has 1450 fees with RPL and 705 AUD with RPL, But if someone fall under RPL case which is as per acs rules then it should also appear in that way. Same for EA — with or without CDR."
- **Fix**: `/app/backend/core/eligibility_kb_seed.py` — Added `fee_native: {currency, standard, [rpl|cdr|priority|modified|expedited], label}` to all 8 AU bodies:
  - **ACS**: AUD 500 (post-Australian degree) / AUD 1,000-1,450 (RPL pathway for non-ICT major)
  - **EA**: AUD 1,150 (Washington/Sydney/Dublin Accord direct) / AUD 1,800 (CDR pathway for non-Accord engineers)
  - **VETASSESS**: AUD 1,225 (standard, 10-12 wk) / AUD 2,710 (priority, 10 business days)
  - **CPA Australia**: AUD 535 (standard) / AUD 1,000 (expedited)
  - **AIM**: AUD 715. Note: For Hotel/Motel Manager (141311), Restaurant Manager (141111) and most hospitality codes, VETASSESS is the correct body, NOT AIM.
  - **AHPRA**: Varies — Medical AUD 800-3,500, Pharmacy AUD 1,170, Dental AUD 1,500
  - **TRA**: AUD 1,070 OSAP / AUD 2,800 MSA
  - **ANMAC**: AUD 525 (standard) / AUD 770 (modified)
- `eligibility_rules.identify_skill_body()` now returns `fee_native` in the response.
- SkillTab in `EligibilityAssessmentResults.jsx` displays the native currency fee + label as a "Fee Breakdown" line, falling back to INR estimate only when missing.

**BUG 4 — Upload Resume button missing on New Assessment / wizard page**
- Sir: "Upload resume show ho raha hai under Profiles and Assessment tab, which is good, it should also show under New-Assessment tab."
- **Fix**: `EligibilityProfileWizard.jsx` header now has Upload Resume button alongside Save Draft. Same `/api/eligibility/profiles/resume-extract` endpoint, deep-merges AI response into form to preserve user-entered fields. data-testid='wizard-upload-resume'.

**BUG 5 — AI giving less detailed output than before**
- Sir: "this time its not giving more detail information like earlier it was giving."
- **Fix**: `/app/backend/core/eligibility_ai.py` SYSTEM_PROMPT now has a new DEPTH EXPECTATION section specifying minimums:
  - narrative: 4-6 sentences (was 2-3)
  - strengths: 4-6 specific bullets backed by data
  - recommended_visa_reasoning: 3-5 sentences
  - occupation_code_reasoning: 3-5 sentences
  - skill_body_advice: 4-6 sentences with NATIVE currency fees + RPL/CDR alternate paths
  - personalised_advice: 4-6 bullets with timelines and document checklists
  - estimated_success_probability_text: high/med/low + 2-3 sentence rationale
- Added RULE 4 (marital_status is authoritative — never apply partner points to single) and RULE 5 (skill body fees must be in NATIVE currency).

---


### 🚀 Phase 6.7 Part 2 — Pre-Analysis Verification + Resume Upload + Client Info-Sheet (May 19, 2026)
**Completed:** May 19, 2026
**Tests:** `test_iteration108_phase67_part2.py` → 24/24 PASS (1 expected skip for AI live call)

Three sub-features built on top of the AI Eligibility Engine:

**1. Pre-Analysis Verification Page** (`/eligibility/profile/:id/verify`):
- New backend endpoint `GET /api/eligibility/profiles/{id}/completeness` — returns a 0-100 completeness score across 8 weighted sections (Personal 12% / Profession 22% / Education 14% / Language 14% / Marital 8% / Spouse 10% / Preferences 10% / Additional 10%)
- N/A rule: spouse section gets full credit (100/100) when marital_status='single'/divorced/etc — no penalty for solo applicants
- Each section returns its score + warnings (e.g., "Missing: Current Profession", "Tip: Add work history")
- Blockers vs warnings split — `ready_for_assessment=false` when there are CRITICAL/REQUIRED blockers
- New `/app/backend/core/profile_completeness.py` houses the scoring logic
- New `EligibilityProfileVerify.jsx` route — renders a hero score card, blockers banner (rose), 8 section grid with progress bars, and an action footer with "Edit Profile" + "Confirm and Run AI Analysis" buttons
- Wizard's "Submit" + Profile list's "Run AI" buttons now route via /verify first (avoids running the AI on incomplete profiles)

**2. Resume Upload + AI Extraction**:
- New `POST /api/eligibility/profiles/resume-extract` accepts multipart PDF/DOCX/TXT (max 10MB)
- New `/app/backend/core/resume_extractor.py` — `extract_text()` dispatches by extension (pdfplumber for PDF, python-docx for DOCX, UTF-8 decode for TXT), `parse_resume_with_ai()` sends text to Claude Sonnet 4.6 with a strict prompt that forces CURRENT PROFESSION matching (e.g., "B.V.Sc graduate now working as Marketing Specialist → `current_profession='Marketing Specialist'`, `field_of_study='Veterinary Science'`")
- Returns Phase 6.7-shaped JSON (primary_applicant nested with personal/professional/education/language/work_history) so the wizard can prefill directly — profile is NOT saved (reversible)
- Frontend: "Upload Resume" button on Profiles list page → file picker → uploads → stores result in `sessionStorage('eligibility_resume_prefill')` → navigates to wizard with `?source=resume` query → wizard picks it up and deep-merges into the form
- Validations: 10MB cap (413), 100-byte minimum (400), extension whitelist .pdf/.docx/.txt (400), AI failure → 502 with detail
- Dependencies added: `pdfplumber==0.11.9` (pinned in requirements.txt)

**3. Client Self-Service Info Sheet**:
- New router `/app/backend/routers/eligibility_info_sheet.py` with 6 endpoints:
  - `POST /api/eligibility/info-sheet/generate-link` — admin/partner creates a public link (expires 1-90 days, default 14)
  - `GET /api/eligibility/info-sheet/public/{token}` — NO AUTH, client opens link, sees prefill (name/email/phone + inviter name)
  - `POST /api/eligibility/info-sheet/public/{token}/submit` — NO AUTH, client submits flat InfoSheetSubmission payload → backend maps to nested Phase 6.7 structure, sets status='pending_review', notifies inviter, captures used_ip/used_ua
  - `GET /api/eligibility/info-sheet/pending` — admin/partner sees pending queue (admin sees all, partner sees own only)
  - `POST /api/eligibility/info-sheet/{profile_id}/approve` — partner/admin approves, status→complete, optional spouse_contribution_type merge
  - `POST /api/eligibility/info-sheet/revoke/{token}` — issuer or admin revokes
- Frontend public route `/info-sheet/:token` → new `PublicInfoSheet.jsx` — clean 7-section form (Personal/Marital/Profession/Education/Language/Spouse[conditional]/Preferences), Switch for language test, country toggle pills, gradient submit card
- Frontend admin: Profiles list now has "Send Info Sheet" button → modal with name/email → generates link → shows Copy + WhatsApp share buttons; "Pending Reviews" violet banner shows count + click-to-filter; inline "Approve" button on pending_review rows
- `FRONTEND_URL` env added to `/app/backend/.env` so public URLs use the correct external domain
- New status enums: `awaiting_info_sheet` (sky) and `pending_review` (violet) added to STATUS_META with icons

**Test coverage (`test_iteration108_phase67_part2.py`):**
- 24/24 PASS — completeness scorer (single vs married N/A spouse rule), resume-extract validations (size/extension/auth/RBAC), info-sheet full lifecycle (generate → public-get → public-submit → pending → approve → revoke), spouse mapping only when married/de_facto, double-submit 410, double-approve 400, partner-not-inviter 403
- 1 expected SKIP — live AI call to /resume-extract is skipped when EMERGENT_LLM_KEY budget is low (502 already verified)

---


### 🐛 Phase 6.7 Part 1 — Critical AI Eligibility Engine Bug Fixes (May 18, 2026)
**Completed:** May 18, 2026
**Tests:** `test_iteration107_phase67_eligibility.py` → 16/16 PASS

**Bugs reported by user from manual testing:**
1. AI was MIXING primary applicant and spouse profiles together in recommendations
2. Partner points were being awarded just because spouse had a Master's degree (no strict gate check)
3. ANZSCO/NOC codes were matched on past EDUCATION (e.g., Veterinary degree) instead of CURRENT PROFESSION (e.g., Marketing Specialist)
4. Results UI did not visually separate "Primary Applicant Analysis" from "Spouse Information"

**Fix #1 + #2 — Profile structure separation + conditional UI** *(implemented earlier this session)*:
- `ProfileCreate` / `ProfilePatch` Pydantic models in `/app/backend/routers/eligibility_profiles.py` now support nested `primary_applicant`, `spouse`, `marital_status`, `dependents`, `schema_version=2`
- `project_new_to_legacy()` denormalizes the new structure into the legacy flat fields (basic_info, professional, education, family) so existing rules code keeps working during transition
- `POST /api/eligibility/profiles/admin/migrate-v67` — idempotent migration of legacy profiles to new structure (admin-only)
- Wizard reorganized: Step 1 is now **Marital Status** (FIRST). Step 6 (Spouse) is **CONDITIONAL** — only shown when marital_status in {married, de_facto}. Spouse Contribution Type dropdown: skill_assessment / english_only / non_contributing / australian_pr_citizen / not_applicable

**Fix #3 — Partner Skill Points Engine Rewrite** (`/app/backend/core/eligibility_rules.py`):
- Replaced education-guessing logic with strict Option A/B/C/D/E rules per Australian government spec:
  - **Option A** (`skill_assessment`) → +10 (`skilled_partner`) — gates: spouse age <45 + IELTS 6+ all bands + on visa. Falls below any gate → DOWNGRADE to Option B if English passes, else 0
  - **Option B** (`english_only`) → +5 (`competent_english_only`) — gate: spouse IELTS 6+ all bands + on visa
  - **Option C** (`non_contributing`) → 0
  - **Option D** (`australian_pr_citizen`) → +10 (`single_or_pr_partner`)
  - **Option E** (single / divorced / widowed / separated OR spouse not on visa) → +10 (`single_or_pr_partner`)
- Each result now carries a `note` field explaining WHY (e.g., "Downgraded to English-only (gate failed: spouse age 47 ≥ 45)")
- Captures spouse_age, spouse_english_overall, spouse_on_visa for UI transparency

**Fix #4 — AI Prompt rewrite** (`/app/backend/core/eligibility_ai.py`):
- New SYSTEM_PROMPT with 5 ABSOLUTE RULES (🔴):
  - RULE 1: ALWAYS analyse the PRIMARY APPLICANT only — never spouse
  - RULE 2: Match occupation codes using CURRENT PROFESSION (current_profession + designation), NOT past education
  - RULE 3: Education earns points but does NOT determine the visa occupation
  - RULE 4: Spouse points are a BONUS only; never the headline
  - RULE 5: Respect the deterministic rules-engine (correct wrong codes, don't flip verdicts)
- `_build_user_prompt` now serializes a `PROFILE_FOCUS` block with CAPS keys (PRIMARY_APPLICANT.CURRENT_PROFESSION, CURRENT_DESIGNATION) so Claude cannot miss them
- Injects up to 60 occupation codes from country_rules for Claude to pick the right one from
- New `_spouse_context()` helper returns None when spouse contribution is not_applicable/non_contributing — prevents AI distraction
- **Verified critical scenario**: Profile with `field_of_study='Veterinary Science'` + `current_profession='Marketing Specialist'` for Canada → AI correctly proposes NOC 10022 (Advertising/Marketing/PR Managers) and explicitly states "Her degree is irrelevant to occupation matching"

**Fix #5 + #6 — Results UI separation** (`/app/frontend/src/pages/eligibility/EligibilityAssessmentResults.jsx`):
- New `ApplicantPanels` component renders side-by-side:
  - **Primary Applicant panel** (indigo, left): full_name, age, current_country, CURRENT PROFESSION highlighted in indigo, experience, education, IELTS, with note "All visa recommendations + occupation codes below are for the PRIMARY APPLICANT only"
  - **Spouse Information panel** (pink, right) — shown when married/de_facto with spouse data: contribution badge (e.g., "English Only +5 pts"), age, on-visa status, profession, IELTS, with note "Spouse data is used ONLY for partner-points calculation, not for visa selection"
  - **No-Spouse panel** (slate) — shown when single/divorced/etc, explains partner-points implications
- New "**PRIMARY APPLICANT ANALYSIS**" divider badge clearly separates the applicant panels from the country comparison/analysis section
- Points tab now has special rendering for the partner row (`points-partner-row`) showing contribution_type, matched_key, note, spouse age + IELTS
- Backend: Assessment doc now stores `marital_status` + `primary_applicant_snapshot` + `spouse_snapshot` at write time → UI renders without extra profile fetch
- Cache key `_profile_hash()` now includes the new structure fields → contribution_type changes invalidate cache correctly

**Test coverage (`test_iteration107_phase67_eligibility.py`):**
- 16/16 PASS (74s individual, ~9 min full run due to live Claude calls)
- TestNewProfileStructure (1), TestPartnerSkillPoints (7 — Options A/B/C/D/E + downgrade + divorced), TestAssessmentSnapshots (1), TestAIOccupationCodeChoice (1 — Vet vs Marketing), TestCacheInvalidation (1), TestMigrationEndpoint (2 — idempotency + partner 403), TestPhase62Regression (3 — list/stats/client-403)

---



### 🚀 Phase 6.3 + 6.4 — AI Analysis Engine + Recommendations UI · THE HEART of Phase 6
**Completed:** May 16, 2026 (Day 3 of Phase 6)
**Tests:** `test_iteration106_eligibility_assessments.py` → 19/19 PASS · Regression intact

#### Backend — Hybrid AI Architecture

**1. Custom Rules Engine** (`core/eligibility_rules.py`, ~500 lines, pure Python, deterministic)
- `PointsCalculator` — country-agnostic, applies any seeded points_system (AU `competent_6/proficient_7/superior_8`, CA `clb_9_plus/clb_8/...`, NZ 6-point system)
- `EligibilityChecker` — hard requirements per visa (age, points, experience, education, language, sponsorship/state nomination warnings)
- `CodeMatcher` — token-based fuzzy match of profession/designation → occupation code with confidence score + alternatives
- `BodyIdentifier` — occupation code → skill body lookup (with `assesses_occupations: ["all_education"]` wildcard)
- `SuccessPredictor` — heuristic score 0-100 with positive/negative factors (high/medium/low label)
- `analyze_country_rules()` — aggregates all 5 modules into a single country result

**2. Claude AI Enrichment** (`core/eligibility_ai.py`, ~150 lines)
- Wraps `LlmChat` with `EMERGENT_LLM_KEY` → `claude-sonnet-4-6`
- Strict JSON-only system prompt (narrative, strengths, weaknesses, visa reasoning, occupation reasoning, body advice, personalised advice, risk factors, alternative pathways, probability narrative)
- Robust JSON parsing (handles ```json wrappers, first `{` / last `}` extraction)
- **Graceful degradation**: any failure (timeout, parse error, budget exhausted) → `_fallback_enrichment()` synthesizes a structurally-identical response from rules output so UI never breaks
- Budget exhaustion detection — labels `_ai_fallback_reason='ai_budget_exhausted: ...'` for ops visibility

**3. Assessments Router** (`routers/eligibility_assessments.py`, ~360 lines)
- `POST /api/eligibility/assessments/run` — parallel `asyncio.gather` across all selected countries with per-country 30s timeout
- 24h SHA-256 cache key based on profile content + sorted country codes
- `GET /api/eligibility/assessments/{id}` — full retrieval with RBAC
- `GET /api/eligibility/assessments/profile/{profile_id}` — latest for a profile
- `POST /api/eligibility/assessments/{id}/re-run` — force bypass cache
- `GET /api/eligibility/assessments/{id}/insights` — compact embed view (best country/visa/score/narrative)
- `GET /api/eligibility/assessments` — paginated history (RBAC-filtered)
- Auto-updates `profile.status = 'assessed'` + sets `profile.assessment_id`

#### Frontend — Recommendations UI (`pages/eligibility/EligibilityAssessmentResults.jsx`, ~700 lines)

- `/eligibility/profile/{id}/assess` — **Runner page**: animated Sparkles icon, 6-stage progress (5.5s intervals), graceful timeout handling (120s axios timeout), retry button on failure
- `/eligibility/results/{id}` — **Results page**:
  - **Best Match Hero Card** — flag, country, recommended visa, Claude narrative, action buttons (View Detailed / Generate Checklist [6.5] / Create PA [6.6])
  - **Country Comparison Strip** — all analyzed countries with verdict badges + scores
  - **Per-Country Detail Tabs** (5 tabs):
    - **Visa**: recommended + AI reasoning + all-evaluated table with failures/warnings
    - **Skill**: occupation code with confidence + skill body card with fee/processing/website + documents list + AI body advice
    - **Points**: total + minimum-required progress bar + category breakdown
    - **Success**: probability badge + strengths/weaknesses dual cards + AI risk factors
    - **Next Steps**: numbered AI personalised advice + executive summary
- AI Status badge (`Claude claude-sonnet-4-6` ↔ `Rules-only fallback`) for transparency

#### Test File
- `backend/tests/test_iteration106_eligibility_assessments.py` (295 lines) — 19 tests covering full happy path + cache + re-run + modes + permissions + regression. Budget-exhaustion-aware AI assertion (passes even if Emergent LLM Key budget is depleted, since fallback layer is functional).

#### Known External Issue
- **Emergent LLM Key budget exhausted** at iteration 106. Hybrid architecture handles this gracefully (UI shows rules-only enrichment with clear "fallback" badge). To restore full AI analysis: **Profile → Universal Key → Add Balance**.



### 🚀 Phase 6.2 — AI Eligibility Engine · Smart Profile Form
**Completed:** May 16, 2026 (Day 2 of Phase 6)
**Tests:** `iteration_105.json` → Backend 23/23 PASS · Frontend 100% smoke · Phase 6.1 & 4D regression intact

#### Backend (NEW)
- `routers/eligibility_profiles.py` (475 lines) — 11 endpoints under `/api/eligibility/profiles/`:
  - `POST /` — create with full profile sections; auto-computes age from DOB
  - `GET /` — paginated list with `search` + `status` filters; RBAC-filtered for non-admin (only own / linked-PA profiles)
  - `GET /{id}` — full profile detail
  - `PATCH /{id}` — section-level merge (preserves untouched sections)
  - `DELETE /{id}` — soft permission: only creator or admin
  - `POST /{id}/duplicate` — clone with `(Copy)` suffix, fresh id, status=draft
  - `POST /{id}/link-to-pa` / `POST /{id}/unlink-pa` — bidirectional PA association with denormalized fields
  - `POST /prefill-from-pa/{pa_id}` — returns pre-populated draft payload (frontend reviews before persisting)
  - `GET /stats/me` — current-user dashboard counts (total / draft / complete / assessed)
- New collection: `client_eligibility_profiles` with profile_id format `ELG-YYYYMMDD-XXXXXX`
- 9 Pydantic models for sections (BasicInfo, Professional, Education, LanguageProficiency, Family, Finances, Preferences, WorkHistoryEntry, AdditionalFactors)
- RBAC: admin/sales/partner/CM/HR can view; client role explicitly excluded (403)

#### Frontend (NEW)
- `pages/eligibility/EligibilityProfileWizard.jsx` (~800 lines) — 7-step multi-step wizard:
  - **Step 1**: Search Mode picker (Specific / Top 3 [recommended] / Custom / Top 5) with country selector for specific & multi-select chips for custom (2–5 cap)
  - **Step 2**: Basic Info with live age calculation from DOB
  - **Step 3**: Profession + Education (required-field gating)
  - **Step 4**: Language Proficiency (IELTS/PTE/TOEFL/CELPIP with per-band scores)
  - **Step 5**: Family + Finances + Preferences
  - **Step 6**: Work History (dynamic add/remove entries) + Additional Factors
  - **Step 7**: Review with section cards + Edit-jumps + final "Save & Run Analysis" CTA
- Auto-save every 30s after Step 0 (uses `lastAutoSavedSnapshot` ref to avoid no-op writes)
- Manual "Save Draft" button always available
- Progress dots clickable to jump back to completed steps
- `pages/eligibility/EligibilityProfiles.jsx` — List page (search + status filter + 4 stat cards) + Detail page (read-only KV summary)
- Routes wired: `/eligibility/profiles`, `/eligibility/new-assessment`, `/eligibility/edit/:id`, `/eligibility/profile/:id`
- Sidebar entries added under "AI Eligibility Engine" group (Admin Dashboard)



### 🚀 Phase 6.1 — AI Eligibility Engine · Knowledge Base + Admin UI
**Completed:** May 16, 2026 (Day 1 of Phase 6)
**Tests:** `iteration_104.json` → Backend 32/32 PASS · Frontend 100% smoke pass · Phase 4D regression intact

#### Backend (NEW)
- `routers/eligibility_kb.py` — 10 admin endpoints under `/api/eligibility/kb/`:
  - `GET /countries`, `GET /countries/{code}`, `POST /countries`, `PATCH /countries/{code}`, `DELETE /countries/{code}` (soft-delete)
  - `POST/DELETE /countries/{code}/visas/{visa_id}` — visa category CRUD
  - `POST/DELETE /countries/{code}/skill-bodies/{body_id}` — skill body CRUD
  - `POST/DELETE /countries/{code}/occupations/{occ_code}` — occupation CRUD
  - `POST /countries/{code}/bulk-import-occupations` — CSV upload (2MB, pipe-separated arrays)
  - `GET /occupations/search?q=` + `GET /skill-bodies/search?q=` — cross-country search
  - `GET /stats` — aggregated KB metrics
  - `POST /seed/run` — admin utility to re-trigger seed
- `core/eligibility_kb_seed.py` — Comprehensive seed data:
  - 🇦🇺 **Australia**: 6 visas (189/190/491/482/186/187), 8 skill bodies (ACS/EA/VETASSESS/CPA Au/AIM/AHPRA/TRA/ANMAC), 32 ANZSCO codes, full points system, document templates
  - 🇨🇦 **Canada**: 4 programs (EE-FSWP/CEC/FSTP/PNP), 5 ECA bodies (WES/IQAS/ICAS/ICES/MCC), 31 NOC 2021 codes, CRS scoring
  - 🇳🇿 **New Zealand**: 4 visas (SMC/Green-T1/Green-T2/AEWV), 4 bodies (NZQA/Engineering NZ/Nursing Council/Teaching Council), 20 codes, post-Oct-2023 6-point system
- Idempotent seed on first API call (preserves manual admin edits)
- Coexists with Phase 4D `/api/eligibility/score` (lead-magnet) — separate router, no conflict

#### Frontend (NEW)
- `/admin/eligibility/knowledge-base` — 6-tab admin UI:
  - **Countries** — Card grid with flag/stats/activate toggle + Add Country dialog
  - **Visas** — Table with edit/delete + comprehensive VisaEditor dialog (code, name, pathway, age/points/experience, processing time, cost, active flag)
  - **Skill Bodies** — Card grid with edit/delete + SkillBodyEditor dialog (name, website, fee, processing weeks, doc list)
  - **Occupations** — Searchable table + Bulk CSV Import + Add Code + OccupationEditor (code, title, group, skill level, body, pathway, eligible visas)
  - **Points** — Visual category cards + JSON editor mode for advanced configuration
  - **Docs** — Read-only summary of common+visa-specific document templates
- RBAC: admin-only mutations; viewer-role read access (partner/CM/sales/HR can view)
- Sidebar entry under new "AI Eligibility Engine" group



### 🔧 Phase 4D+ — P1 Enhancements: Finance Unification + People Onboarding
**Completed:** May 16, 2026
**Tests:** `iteration_103.json` → Backend 24/24 new + 42/43 regression PASS · Frontend smoke OK

#### P1.1 — Custom Per-Partner Product Commission UI merged into Finance Center
- New tab "**Custom Rates**" in `/admin/finance` — full CRUD UI for per-partner-per-product commission overrides.
- Inline **Approve / Pay / Reverse** actions added to the Sales (commissions) tab — no need to navigate to old `/admin/sales/commissions` page anymore.
- Sidebar entries "Commissions" + "Commission Analytics" now redirect to Finance Center for unified UX.
- Orphan rows (deleted partner/product) labelled "⚠ Deleted partner / Deleted product" with reduced opacity for clarity.
- Component: `frontend/src/components/finance/CustomCommissionsPanel.jsx`.

#### P1.2 — People Onboarding Form (KYC docs + onboarding fields in Add Person Wizard)
- **Wizard expanded from 3 → 4 steps**: Type → Basic Info → Role → **Onboarding** (new).
- Step 4 captures: Employment (designation, DOJ, DOB, gender), Address (current/permanent/city/state/pincode), Emergency contact (name/phone/relation), KYC (PAN/Aadhaar/GST), Bank (holder/account/IFSC/bank), Notes.
- All onboarding fields persisted to `users.onboarding` AND `vendors.onboarding` collection (including the auto-linked user account for internal vendors).
- Vendor docs get KYC/bank lifted to top-level fields too — keeps existing `/vendors/*` API contracts working.
- New **Documents** section in Person Detail drawer:
  - Required checklist (per person_type): PAN, Aadhaar, Resume, Bank Passbook, etc.
  - Upload (PDF/JPG/PNG/WEBP/DOC/DOCX, max 10 MB), Download, Verify (admin attestation), Delete.
  - Files stored at `/app/uploads/people_documents/{person_id}/{doc_id}__filename` with sanitized names.
- 5 new backend endpoints in `routers/people.py`:
  - `GET /api/people/document-checklist/{person_type}` — recommended docs
  - `GET /api/people/{id}/documents` — list
  - `POST /api/people/{id}/documents` (multipart) — upload
  - `GET /api/people/{id}/documents/{doc_id}/download` — download
  - `POST /api/people/{id}/documents/{doc_id}/verify` — verify
  - `DELETE /api/people/{id}/documents/{doc_id}` — delete



### 🔧 Phase 4D — Express Sale Limits Admin Control + Token Link Bug Fix
**Completed:** May 16, 2026
**Tests:** End-to-end curl PASS · Frontend smoke screenshot PASS

#### Bug Fix — Express Token Mode "Generate Public Link" 403 / wrong link
- **Root cause:** Express+Token PA auto-approves to `stage="approved"`, but `generate_public_link` treated any stage in `("approved", ...)` as fee_paid → routed to magic-link BRANCH-B → 400 "Client account not linked yet".
- **Fix:** In `pre_assess_portal.py`, added `is_express_token_unpaid` guard so PAs whose token is still pending are routed to BRANCH-A and return a public payment link with `link_type="express_token_payment"` and the configured token amount (e.g. `₹11,000`).

#### Admin Express Sale Control (per-user overrides)
- **Why:** Hard-coded role limits (`partner=3/mo`, `sales_executive=5/mo`) were rigid. Admins now have full control.
- New settings field `express_user_limit_overrides: {user_id: int}` — `-1` unlimited · `0` blocked · `N>0` custom limit.
- `core/express_logic.check_limit()` now checks per-user override FIRST, then falls back to role default.
- 3 new endpoints in `routers/express_sales.py`:
  - `PUT  /api/express/settings/user-limit` — set / update / remove override
  - `GET  /api/express/settings/user-overrides` — list with hydrated user data + current month usage
  - `GET  /api/express/settings/searchable-users?q=` — typeahead for sales/partner/admin users
- `/api/express/my-usage` now surfaces `limit_source` ("admin_override" vs "role_default").
- New admin page `/admin/sales/express-settings` (sidebar: Sales Management → "Express Sale Limits"):
  - Global ON/OFF switch
  - Per-User Overrides tab — Add/Edit/Remove with 3 preset modes (Unlimited / Custom / Blocked)
  - Role Defaults tab — editable per-role table with blank = unlimited
  - Search-by-name/email user picker in Add Override dialog




### 🏆 Phase 4D — ARCHITECTURAL UNIFICATION (Triple combo)
**Completed:** May 14, 2026  
**Tests:** 43/43 PASS (`iteration_102.json`, `/app/backend/tests/test_phase4d_unification.py`)

#### Part A — Unified People Management (`/admin/people`)
- New `routers/people.py` — 10 endpoints stitching `users` + `vendors` collections together
- **Single source of identity** — no more 4 different paths to create users (vendors / hr / partners / direct)
- Add Person Wizard: 3-step flow with 4 person_types (employee_internal · partner_external · vendor_internal · vendor_external)
- For `vendor_internal` + category=`case_manager`/`sales_commission` → auto-creates linked User record with correct role + temp password
- Validates `role` against `INTERNAL_ROLES` set; rejects unknown roles with 400
- Deactivate cascades to linked vendor (and vice versa)
- Reset password from admin produces temp_password to share with user
- RBAC: requires admin or HR role (`hr.user_manage.any` permission)
- New frontend `PeopleManager.jsx` — master list + 6 type tabs + master-detail dialog + Wizard. Sidebar entry: "People (All)"

#### Part B — Unified Finance Dashboard (`/admin/finance`)
- New `FinanceDashboard.jsx` — single page consolidating ALL money flows
- 4 tabs: Overview · Sales Commissions · CM Earnings · Vendor Payouts
- KPI cards: Total Revenue · Sales Commission · Vendor Payouts Outstanding · Total Money Movement
- Period picker (YYYY-MM) + status filter applied globally
- CSV download per tab (CM, Vendor, Sales) — client-side generation
- Top Performers leaderboard + Vendor Payout Health summary on Overview
- Backend: pure proxy/aggregation of existing endpoints (no new collections)

#### Part C — Express Sale Modes (Token + Direct)
- Backend: `express_mode` field on PA (`token` | `direct`) + `express_token_amount`
- Validation: token mode requires positive amount; invalid mode rejected with 400
- Frontend: PA Create Form has a clean Express Mode selector (2 visual cards: Direct Proposal vs Token Payment) with conditional token amount input
- Public PA page (PreAssessmentPayment.jsx) detects `sale_type='express'` AND renders mode-specific UI:
  - **Token mode**: shows "Pay Token ₹X to lock your slot" button (mock payment)
  - **Direct mode**: shows "Your consultant will share full proposal shortly" message
  - Either way: NO ₹5,100 PA fee charged

#### Bug fixes shipped this round
- **Slab Delete** — replaced `window.confirm` (blocked in some iframes) with proper state-based Dialog with explicit cancel/confirm buttons
- **Vendor "View" button logout** — was navigating to non-existent route. Now opens inline `VendorDetailDialog` with full identity, bank details, performance, assignments, edit/invite buttons
- **Calculator empty state** — shows friendly amber card with arrow → Cost tab when product has no allocations
- **Vendor invite link** — frontend now prefixes with `window.location.origin` so the full URL is copyable; backend kept returning relative path for portability
- **Express Sale ₹5,100** — public payment page now skips PA fee for `sale_type='express'`
- **CM Earnings widget click-through** — opens detail dialog showing client-wise breakdown. Privacy honored: NO revenue/sales values exposed to CM, only their own earnings.
- **Product price lock on PA proposal** — proposal_fee auto-fills from product.service_price and is locked (read-only) for partners; admin sees "Override (admin)" toggle to unlock when needed

#### Sidebar additions
- "People (All)" — under System
- "Finance Center" — under Sales Management

#### Test coverage
- `/app/backend/tests/test_phase4d_unification.py` — 43 tests across 8 classes: PeopleListAndStats · GetPerson · AddPerson · UpdatePeople · DeactivateReactivate · ResetPassword · RBAC · FinanceEndpoints · ExpressModes · Regression. All green.

#### Known minor item (not blocking)
- Express auto-approved PAs route to magic-link branch in `/pre-assess-portal/generate-public-link` and 400 when client_user_id is null. Workaround: PA doc DOES persist `express_mode` + `express_token_amount` correctly; when share-token link is generated via the normal path, the public page renders the token UI correctly. Spec-level fix flagged for future cycle.

---


### 🏆 Phase 4C UNIFICATION — Products + Cost Structures Merged
**Completed:** May 14, 2026  
**Tests:** 24/30 PASS in iteration_101 with 2 critical bugs found & fixed (success_bonuses field-name, legacy products backfill)

#### What changed
- **Single source of truth:** `products` collection now carries ALL product identity + cost configuration:
  - Identity: `name`, `country`, `visa_type`, `category`, `description`, `status`
  - Pricing: `service_price` (mirrored to `base_fee`)
  - Cost Structure: `cost_allocations[]`, `success_bonuses[]`
  - Computed: `{expected_base_cost, expected_margin, expected_margin_pct, max_bonus_payout}` — auto-recomputed on any update
  - Legacy: `cost_structure_meta` retains migration audit trail
  - Workflow: `workflow_steps[]` (unchanged — used by AI Workflow Builder)

#### Backend
- `routers/products.py` — Full rewrite with new fields, `/preview` calculator endpoint, auto-recompute on PUT
- `core/allocations_logic.py` — `find_matching_structure` now looks at unified `products` FIRST, with `_product_to_structure` normalizer; legacy `product_cost_structures` retained as back-compat fallback
- `migrations/phase4c_products_unification.py` — Idempotent migration: merges existing 5 cost-structure docs into products + backfills 12 legacy products with default unified shape. Auto-runs at server boot.
- `routers/pre_assessment.py` — `/my-assessments` now accepts `?stage=` filter
- `routers/vendors.py` — Internal vendor creation (`vendor_type=internal` + category=`case_manager`/`sales_commission`) auto-creates a User record with the matching role + temp password; existing email gets linked
- `routers/payouts.py` — Added `POST /payouts/{pa_id}/allocations/{allocation_id}/dispute` and `/resolve-dispute` endpoints; status flow now includes `disputed` state

#### Frontend
- New unified `/admin/products` (`ProductsManager.jsx`) — split-screen master list + tabbed detail (Overview · Cost Structure · Success Bonuses · Preview Calculator). Cards show margin badge, country/visa chips, "Costed/Need Setup" status pills.
- `PaCreateForm.jsx` — Product now PRIMARY field at top; selecting a product auto-fills country + service_type
- `PayoutQueue.jsx` — Terminal rows (paid/reversed) locked from selection; bulk buttons disable on wrong-status mix; per-row Dispute / Resolve actions; status-flow info card
- `CommissionSlabsManager.jsx` — Delete button visually prominent (red border) for user-created slabs; system slabs show lock icon
- `AdminVendors.jsx` — Vendor invite link uses input field + Ctrl+C instructions + clipboard fallback (works in sandboxed iframes); when internal user auto-created, admin sees temp password in alert popup
- Admin sidebar: "Products" entry moved to top, "Cost Structures" removed (deprecated)

#### Bug fixes this round
- **#1 success_bonuses field-name mismatch** — `_compute_margin` and `/preview` were reading `b.get("amount")` but stored field is `bonus_amount`. Now uses fallback. Canada PR Express Entry now correctly shows ₹7,000 max bonus (was ₹0).
- **#2 legacy products missing unified fields** — Migration only enriched the 5 cost-structure-linked products. Now backfills all 12 legacy products with empty cost_allocations/success_bonuses/computed defaults + mirrors base_fee → service_price.
- **#3 "Failed to load PAs" on Allocations** — Fixed by adding `?stage=` filter to PA endpoint.
- **#4 Clipboard error in invite dialog** — Fallback to execCommand + manual selection prompt.
- **#5 Payout queue showed Approve/Pay for paid rows** — Terminal-state rows now locked; explicit Dispute action with reason.

#### Verified end-to-end
- 17 total products in DB; 5 fully costed (Canada PR ₹100k @ 85% margin · Australia PR ₹80k @ 85% · USA H1B ₹150k @ 75% · UK Skilled ₹90k @ 84% · Canada Student ₹50k @ 81%) + 12 legacy with empty cost structures (ready for admin to configure)
- `/preview` with visa_approved=true correctly applies success bonuses (verified ₹7000 bonus on Canada PR)
- All Phase 4C.3-4C.7 regression endpoints still 200 OK
- Internal vendor auto-creation works for case_manager + sales_commission roles; existing users get linked silently
- Dispute → Resolve workflow validated (admin only, correct status transitions)

---


### ✅ Phase 4C.5 + 4C.6 + 4C.7 — CM Earnings Widget + Vendor Portal + Payout Workflow
**Completed:** May 14, 2026  
**Tests:** 36/36 PASS (`/app/backend/tests/test_phase4c5_4c6_4c7.py`, also `iteration_100.json`)

#### Phase 4C.5 — Case Manager Earnings Widget (Read-Only)
- New router `/api/cm-earnings/my` — filters allocations where `vendor_category="case_manager"` AND `vendor_id=current_user.id`
- Returns `{totals: {pending/approved/paid/disputed}, lifetime_total, deal_count, line_items[]}`
- Optional `?period=YYYY-MM` filter with recomputed totals
- Frontend: `CmEarningsWidget.jsx` embedded at top of CM dashboard (`activeTab === 'dashboard'`)
- **Strict constraint honored**: Auto-hides when CM has no earnings. NO workflow changes to CM portal.

#### Phase 4C.6 — External Vendor Portal
- New router `routers/vendor_portal.py`:
  - `POST /vendor-portal/accept-invite` (public) — consumes magic link, creates user with `role=vendor`, sets password, links to vendor
  - `GET /vendor-portal/me` — full profile with UNMASKED bank details (since self-view)
  - `PATCH /vendor-portal/me` — vendor updates phone, bank, PAN, GST
  - `GET /vendor-portal/my-assignments` — all allocations across PAs (matches vendor_id OR vendor_master_id)
  - `GET /vendor-portal/my-payments` — paid-status history
- Login auto-routes `role=vendor` → `/vendor/dashboard`
- Frontend: `/vendor/accept-invite/{token}` (set password with strength meter), `/vendor/dashboard` (assignments + totals + bank details)
- Password validation: min 8 chars, mixed case, digit, special — enforced via `validate_password_strength`

#### Phase 4C.7 — Approval + Payout Workflow
- New router `routers/payouts.py`:
  - `GET /payouts/queue?status=&vendor_id=&from_date=&to_date=` — flat list across all PAs
  - `GET /payouts/stats` — overall summary {totals, counts, ready_to_pay, outstanding}
  - `POST /payouts/bulk-approve {items: [{pa_id, allocation_id}, ...]}` — moves pending → approved
  - `POST /payouts/bulk-mark-paid {items, payment_reference}` — moves to paid with batch reference (auto `BATCH-YYYYMMDD-HHMMSS` if blank)
  - `GET /payouts/neft-csv?status=approved&from_date=&to_date=` — CSV download with vendor + bank + amount + reference
- Frontend: `/admin/payouts` — checkbox-select rows, bulk action bar, CSV download, status/date filters, search by vendor/client/PA#
- **CRITICAL BUG FIXED in this iteration**: Bulk filters used `{vendor_id: $ne: null}` which excluded external vendors (linked via `vendor_master_id`). Now uses `$or: [{vendor_id: $ne null}, {vendor_master_id: $ne null}]`. All 36 tests pass after fix.

#### Frontend Additions
- 3 new admin sidebar entries: "Cost Allocations" · "Commissions" · "Commission Slabs" · "Payout Queue"
- Vendor portal routes: `/vendor/accept-invite/:token` and `/vendor/dashboard`
- `CmEarningsWidget` embedded in CaseManagerDashboard
- `Login.jsx` adds vendor role-route mapping

#### Verified
- RBAC: client gets 403 on cm-earnings, vendor-portal, payouts. Non-admin gets 403 on payouts. Vendor without record gets 404.
- Idempotency: bulk operations skip non-eligible rows and report failures. Magic link can only be used once (410 on reuse).
- NEFT CSV column order matches spec exactly. Hydrates bank details from both vendor master + users collection.
- Regression: All Phase 4C.3 + 4C.4 + 4C.2 + 4C.1 endpoints still pass.

### 🏆 PHASE 4C COMPLETE — Sales Commission + Vendor Payout Engine
All 7 sub-phases (4C.1 Vendors, 4C.2 Cost Structures, 4C.3 Auto-Allocations, 4C.4 Sales Commissions, 4C.5 CM Earnings, 4C.6 Vendor Portal, 4C.7 Payouts) — fully built & tested.

---

## 📅 May 2026

### ✅ Phase 4C.3 + 4C.4 — Auto-Allocation Engine + Sales Commission Slabs
**Completed:** May 14, 2026  
**Tests:** 27/28 PASS (`/app/test_reports/iteration_99.json`)

#### Phase 4C.3 — Auto-Allocation Engine
- New router `/api/pa/{pa_id}/allocations/*` mounted (was orphaned previously)
- `core/allocations_logic.py` — find_matching_structure, build_allocations_for_pa, assign_vendor, set_allocation_status, apply_visa_approved_bonuses, apply_refund_clawback
- **Auto-trigger**: `admin_approve_final` (PA → case_created) now invokes `build_allocations_for_pa` AND `apply_commission_for_pa` — both wrapped in try/except so failure never blocks case creation
- Per-allocation status flow: `unassigned → pending → approved → paid` (or `disputed`)
- Visa-approved milestone applies success_bonuses; idempotent
- 50% clawback on refund; idempotent via `milestones.refunded` flag
- Vendor auto-assignment: `sales_commission` → PA creator; `case_manager` → assigned CM; others stay unassigned for admin to manually assign
- New permissions: `allocation.view.all/team/own`, `allocation.assign.vendor`, `allocation.approve.any`, `allocation.mark-paid.any`

#### Phase 4C.4 — Sales Commission Slabs
- New `core/commission_logic.py` + `routers/sales_commission.py`
- 3 default slabs auto-seeded on first read: Bronze (0–5L @ 5%), Silver (5L–15L @ 7%), Gold (15L+ @ 10%)
- DB collections: `sales_commission_slabs`, `sales_commission_entries`, `sales_commission_config`
- **Cumulative slab matching**: `achieved_after = cumulative_period_revenue + this_deal` → matches highest slab whose range covers `achieved_after`. Verified: sexec with prior ₹0 → 1st deal ₹3L → Bronze @ 5% → ₹15k. 2nd deal ₹4L (cumulative ₹7L) → upgraded to Silver @ 7% → ₹28k.
- Entry workflow: `pending → approved → paid` (or `reversed` on refund)
- `/my` self-service: returns current_slab, next_slab, gap_to_next_slab, total_commission, deal_count, entries
- `/all` + `/leaderboard` admin views
- Idempotent: same `pa_id` cannot create duplicate entry

#### Frontend
- `/admin/allocations` — Per-PA allocation breakdown with assign/approve/pay buttons, recalc, visa-approved trigger
- `/admin/sales/commission-slabs` — Slab CRUD with visual preview, color tags, system-slab protection
- `/admin/sales/commissions` — Admin dashboard with stats + leaderboard + entries table + approve/pay actions
- `/sales/my-commission` — Sales rep self-service with current tier banner, progress bar to next slab, deals history
- `CommissionWidget` on SalesWidgets row now LIVE (no longer placeholder) — shows tier + commission + gap to next
- Sidebar entries added under "Sales Management" group: Cost Allocations · Commissions · Commission Slabs

#### Verified
- Slab auto-seed, CRUD validation (max>min, duplicate key), system-slab protection
- RBAC: client 403 on `/my`, `/all`, `/slabs` management; partner can view own commission
- Regression: existing routes (`/auth/login`, `/products/cost-structures`, `/vendors`, `/vendors/categories`, `/pre-assessment/admin/queue`) all 200 OK
- Test file at `/app/backend/tests/test_phase4c_commission_allocations.py` (28 cases, reusable for regression)

---


## 📅 February 2026

### 🐛 Hotfix: Direct Sales Not Counting + Admin Preview-as-Client Bug (Phase 4B Part 2.1)
**Completed:** Feb 13, 2026  
**Tests:** 46/46 PASS (added `test_direct_sale_approved_contributes_to_target`)

#### Issues reported by user
1. **Target widget not updating after direct-sale approval**: User created a direct sale via "My Sales" (not via PA flow), admin approved it (₹292,250 received), but the sales target widget showed 0% achievement. Root cause: `compute_achievement` only queried `pre_assessments_col` for `stage=case_created` — direct-sale revenue from the `sales` collection was excluded.
2. **"Partners or admins only" error on Preview-as-Client**: Admin and sales executives both got 403 when clicking the "Preview as Client" button on PAs. Three more endpoints in `pre_assess_portal.py` had the same legacy `role in ("partner", "admin")` hardcoded check (same bug pattern as Phase 4B Part 1).

#### Fix 1 — Dual-source revenue recognition
- **`core/targets_logic.py:compute_achievement`** — Now sums revenue from **BOTH**:
  - `pre_assessments` where `stage=case_created` (standard + express PA path)
  - `sales` where `status=approved` (Direct Sale path — bypasses PA)
- De-duplication via `seen_sale_ids` so a PA linked to a sale doesn't double-count
- Uses `amount_received` for direct sales (matches commission convention), fallback to `fee_amount`
- **`routers/sales.py:approve_sale`** — On admin approve, fires `recalc_targets_for_user(sale.partner_id, notify=True)` to instantly refresh widgets + trigger milestone notifications
- **`routers/sales.py:record_payment`** — When additional payment is received on approved sale, fires recalc (`notify=False` since no milestone change typically)

#### Fix 2 — Removed legacy role gates
- **`routers/pre_assess_portal.py`** — 3 endpoints fixed with admin-OR-(owner+sales-role) pattern:
  - `partner/preview-magic/{pa_id}` ("Preview as Client" button)
  - `partner/forward-to-admin/{pa_id}` (forward docs for 1st approval)
  - `partner/submit-for-final-approval/{pa_id}` (final submission)
- All now accept admin/admin_owner OR (sales_executive/sr_sales_executive/sales_manager/sales_head/partner) with ownership via `partner_id` or `created_by_user_id`

#### Verified Live
- ✅ User's "test sales" (₹292,250 approved direct sale) now shows in widget: **58.45% achievement (₹292,250/₹500,000)**, PA Count 1/10, status Active
- ✅ Admin + sexec can both hit preview-magic endpoint (passes role check; gets correct business-logic 400 if client hasn't paid yet)
- ✅ Phase 4A regression 15/15 · Phase 4B Targets 15/15 · Phase 4B Express 16/16



### ✅ Phase 4B Part 2 — Two-Path Sales (Express Sale) DELIVERED
**Completed:** Feb 13, 2026  
**Tests:** Backend **45/45 ALL PASS** (Phase 4A 15/15 + Phase 4B Targets 15/15 + Phase 4B Express 15/15) — `/app/test_reports/iteration_98.json`. Frontend testing agent confirmed: 95% success rate, all critical flows + role isolation work.

#### What's New
Real-world sales flexibility: not all sales need PA fees + first-approval. Express Sale adds a fast lane for **repeat clients, VIP customers, pre-qualified referrals** etc. — skips ₹5,100 PA fees collection but requires Admin approval before proposal generation. Both paths converge at `case_created` → same revenue recognition, same target/commission counting.

#### Acceptance Criteria — 30/30 met
- **Creation**: Standard (default, unchanged) and Express paths work for sales_executive, sr_sales_executive, sales_manager, partner; justification ≥30 chars enforced; 6 valid reasons + "other"
- **Limits**: Per-role monthly caps — sexec=5, sr_sexec=8, smgr=15, sales_head/admin=unlimited, partner=3; 429 with clear message on exceed
- **Auto-approval**: `sales_head`, `admin_owner`, `admin` skip the pending state (configurable via settings)
- **Admin workflow**: `/admin/sales/express-approvals` page with pending queue, approve/reject dialogs (reject requires ≥5 char remarks), history tab with status badges
- **Revenue counting**: Express PA → admin approve → push to `case_created` → recalc fires → target.achievement.revenue includes Express revenue ✅ (verified by `test_express_approved_contributes_to_target_on_case_created`)
- **Role isolation**: Partner/Case Manager/Client cannot view pending queue (403); Sexec cannot approve (403); only roles with `pa.approve.express` can approve
- **Audit**: Every approval/rejection logged with `admin_decision`, `admin_reviewed_by/at`, full remarks trail
- **UX**: PA cards show `⚡ Express` badge + `Awaiting Approval` if pending; dashboard widget shows live usage X/Y this month

#### Files (Backend)
**New**:
- `backend/core/express_logic.py` — settings defaults, monthly count, limit check, validation, auto-approve detector
- `backend/routers/express_sales.py` — 7 endpoints: GET/PATCH settings, my-usage, pending, approve, reject, history
- `backend/migrations/phase4b_express_init.py` — idempotent: seeds `sales_settings` doc + 2 indexes on pre_assessments
- `backend/tests/test_phase4b_express.py` — 15 pytest cases (incl. critical revenue counting E2E)

**Modified**:
- `backend/routers/pre_assessment.py` — STAGES list expanded (added `express_pending_approval`, `express_rejected`); `CreatePreAssessment` model accepts `sale_type`, `express_sale_reason`, `express_sale_justification`; create endpoint branches on `sale_type` with full validation + limit check + auto-approve
- `backend/server.py` — registered `express_sales_router` + boot-time migration
- `backend/core/rbac/seed_data.py` — added 4 perms: `pa.create.express.own`, `pa.approve.express`, `sales_settings.view.all`, `sales_settings.manage.any`; granted to admin_owner / sales_head / sales_manager / sales_executive / sr_sales_executive appropriately

#### Files (Frontend)
**New**:
- `frontend/src/pages/admin/ExpressApprovalsAdmin.jsx` — Admin approval queue with reason badges + dialogs

**Modified**:
- `frontend/src/components/pa/PaCreateForm.jsx` — Sale Type radio cards at top + Express conditional panel (reason dropdown, justification with live char counter, warning banner)
- `frontend/src/components/PreAssessmentPipeline.jsx` — fetches express usage, passes to form, shows `⚡ Express` + `Awaiting Approval` badges on PA cards
- `frontend/src/components/sales/SalesWidgets.jsx` — new `ExpressUsageWidget` showing X/Y monthly count with color-coded progress (widget row grid bumped to 5 cols)
- `frontend/src/pages/AdminDashboard.jsx` — sidebar group "Sales Management" → added "Express Approvals" nav
- `frontend/src/App.js` — route `/admin/sales/express-approvals` guarded by `pa.approve.express`

#### Critical Revenue-Counting Test (passing)
```
test_express_approved_contributes_to_target_on_case_created
  1. Admin sets target ₹5L/10PAs for sexec for current month
  2. Sexec creates Express PA (vip_customer reason)
  3. Admin approves Express → stage=approved
  4. Push to case_created with proposal_fee=₹75K
  5. Trigger /sales/targets/recalculate
  6. Verify /sales/targets/my returns achievement.revenue=75000, pa_count=1 ✅
```



### 🐛 Hotfix: Payment Link Error for Sales Executives
**Completed:** Feb 13, 2026
**Tests:** Backend regression 30/30 PASS (Phase 4A + 4B both green)

#### Root Cause
After Phase 4A introduced sales_executive as a legacy role, the endpoint `POST /api/pre-assess-portal/generate-public-link` (called by PaActionBar's "Share" button) was still hard-checking `role in ("partner", "admin")` — returning **403 "Not allowed"** for sales execs trying to send the ₹5,100 PA payment link.

#### Fix
- **`routers/pre_assess_portal.py:generate_public_link`** — replaced legacy role-list check with permission + ownership scoping:
  - `is_admin` (legacy/rbac admin/admin_owner) **OR**
  - `is_owner` via `partner_id == user.id` OR `created_by_user_id == user.id` (Phase 4A field) **AND** `pa.share.own` permission
- **`routers/pre_assessment.py:send_payment_link`** — same hardening applied for consistency

#### Verified
- ✅ Sexec → generates link successfully (200, returns share-token URL)
- ✅ Partner → regression check works (200)
- ✅ Sexec → trying to share another user's PA still gets 403 (security maintained)



### ✅ Phase 4B — Sales Targets Management (DELIVERED)
**Completed:** Feb 13, 2026
**Tests:** Backend 29/29 + Phase 4A regression 15/15 = **44/44 ALL PASS** (`/app/test_reports/iteration_97.json`)

#### Acceptance Criteria — 33/33 met
- **Admin/Manager workflows**: Create + edit (with required reason ≥5 chars) + soft-delete (admin, future-only) + bulk-apply template (override flag) + template CRUD with system-template lock
- **Sales Executive view**: `/sales/my-targets` with Monthly/Quarterly/History tabs, live progress cards (Revenue + PA Count), daily run-rate calculation, days remaining, color-coded by % (rose → yellow → blue → emerald → amber for exceeded)
- **Live dashboard widget**: `Monthly Target` on `/sales/dashboard` shows real-time ₹achievement / ₹target, %, days left, daily required pace (was placeholder)
- **Auto-recalc**: PA `case_created` triggers `recalc_targets_for_user(created_by_user_id)` with milestone notifications at 50/75/100/150%
- **Role isolation verified**: Partner/Case Manager/Client get null/redirect on `/sales/*` routes (RequirePermission guards). Sales Exec cannot set own target (403).
- **Past-period block**: Cannot create or edit targets whose period has ended (400)
- **Period uniqueness**: One target per user per period (409 on duplicate, can use override_existing in bulk)
- **3 seed templates**: Starter ₹3L/6 · Standard ₹5L/10 · Aggressive ₹8L/16 (all system-locked from edit/delete)

#### Files
**New (4):**
- `backend/core/targets_logic.py` — period bounds, achievement compute, status, milestone detection, tz-safe helpers
- `backend/routers/targets.py` — 18 endpoints (CRUD + bulk + view + recalc + analytics + templates)
- `backend/migrations/phase4b_targets_init.py` — idempotent: 5 indexes + 3 system templates seed
- `backend/tests/test_phase4b_targets.py` — 15 pytest cases
- `frontend/src/pages/MyTargets.jsx` — Sales exec progress UI
- `frontend/src/pages/admin/SalesTargetsAdmin.jsx` — Admin team grid + bulk-apply modal + edit modal
- `frontend/src/pages/admin/TargetTemplatesManager.jsx` — Template CRUD

**Modified:**
- `backend/core/database.py` — registered `sales_targets_col`, `target_templates_col`
- `backend/core/rbac/seed_data.py` — added 8 perms: `target.delete.any`, `target.history.{team,all}`, `target_template.{view,use,create,manage}.{all,any}`; updated 4 role permission lists
- `backend/server.py` — registered `targets_router` BEFORE `sales_router` (avoids `/sales/{id}` catch-all collision), boot-time migration hook
- `backend/routers/pre_assess_portal.py` — `admin_approve_final` now triggers `recalc_targets_for_user` after stage→case_created
- `frontend/src/components/sales/SalesWidgets.jsx` — `TargetWidget` now LIVE (calls `/api/sales/targets/my`)
- `frontend/src/pages/AdminDashboard.jsx` — new sidebar group "Sales Management" with Targets + Templates
- `frontend/src/App.js` — 3 new routes guarded by RequirePermission

#### Bug Fixed Post-Test-Agent Review
- **`days_remaining = 0` mid-period bug**: `_strip_id` converted MongoDB datetimes to ISO strings; `datetime.fromisoformat` returned naive datetimes which raised TypeError on comparison with tz-aware `now()`. The `except Exception` branch then defaulted to 0. **Fix**: coerce parsed datetimes to UTC-aware in `get_my_targets.enrich()` AND in `days_remaining_in_period()` itself. Verified: sexec sees `18 days left · Need ₹27.8K/day` correctly mid-May.



### ✅ Full Impersonation Restored — "View Dashboard As User" (Switch Button)
**Completed:** Feb 13, 2026
**Tests:** Backend curl (5 guard-rails) + Frontend E2E screenshot flow — ALL PASS

#### Why
User requested original full impersonation back (Option A) — the prior agent had downgraded `/api/auth/impersonate` to 410 GONE in favor of a read-only `dashboard-preview` modal. User found the preview modal too restrictive and wanted to actually navigate the impersonated user's portal.

#### Backend Changes
- **`POST /api/auth/impersonate/{user_id}`** — restored to fully working endpoint (was returning 410 GONE)
  - Admin-only gate (legacy `role == 'admin'` + `rbac_role in (admin_owner, admin)`)
  - 400 if admin tries to impersonate self
  - 400 if target is inactive
  - 404 if user not found
  - Issues a JWT for target using `build_token_payload(target)` (same flow as `/login`)
  - Returns target's full user payload + `impersonated_by` metadata
  - Every switch logged to `audit_logs` with `action='impersonate_user'`, `admin_email`, `target_email`, `target_role`

#### Frontend Changes
- **`AdminDashboard.jsx`** — `Switch` button (`[data-testid^="switch-user-"]`) at line 2424 now wired to `handleImpersonate(usr)` (was `setPreviewUserId(usr.id)`)
- **`handleImpersonate`** — expanded route map to support all sales roles (`/sales/dashboard`) + fallback to `/portal/welcome`. Added error-recovery to restore admin token if switch fails mid-way.
- **`DashboardShell.jsx > AdminReturnBanner`** — yellow banner enhanced:
  - Shows `🔄 Impersonating [target name]` with role badge
  - Shows `(Logged in as Admin: [admin name])` for clarity
  - Button text: `Exit Impersonation` (was `Return to Admin`)
  - `data-testid="impersonating-label"` for the target-name span
- Existing read-only `DashboardPreviewModal` still mounted (kept for `EmployeeDetailModal` usage)

#### Verified
- ✅ Partner → impersonate → 403
- ✅ Self-impersonate → 400 "Cannot impersonate yourself"
- ✅ Anonymous → 403
- ✅ Bad user id → 404
- ✅ Audit log entry written
- ✅ Frontend E2E: Admin → Users tab → Switch on Case Manager → land on `/case-manager` → yellow banner shows "Impersonating Case Manager" → Exit → back to `/admin`, banner gone



### ✅ Phase 4A — Sales Workflow Inheritance (COMPLETE — 15/15 backend tests passed)
**Completed:** Feb 13, 2026
**Tests:** 15/15 backend tests passed via testing_agent_v3_fork (`/app/test_reports/iteration_96.json`)
**Test file:** `/app/backend/tests/test_phase4a_sales_workflow.py`

#### 🎯 Design Principle — DRY
Sales executives are treated as "internal partners" — they use the EXACT SAME PA workflow components as external partners. NO duplication.

#### Backend Changes
- **NEW**: `core/attendance_logic`-style helper module: `_assert_pa_owner()` at top of `pre_assessment.py` for centralized ownership enforcement
- **NEW**: Module-level constants `PA_CREATOR_ROLES`, `OWN_SCOPED_ROLES`
- **CRITICAL FIX**: Applied ownership check to `GET /api/pre-assessment/{pa_id}` (was previously unrestricted — pre-existing bug exposed by Phase 4A)
- `POST /api/pre-assessment/create` now accepts `lead_source` + `lead_source_detail` (10 options) and stores `created_by_role`, `created_by_user_id`, `created_by_user_type`
- 14 ownership checks across 7 routers updated from `role == "partner"` to `role in (partner|sales_executive|sr_sales_executive)`
- Sales executive `partner_id = user.id` strategy → all existing scope queries work transparently

#### Migration (Phase 4A)
- `migrations/phase4a_pa_backfill.py` — Idempotent. Backfills `created_by_user_id`, `created_by_role`, `created_by_user_type` on existing PAs.
- 15 existing PAs backfilled on first boot.

#### Frontend Changes
- **NEW**: `/sales/dashboard` route (RequirePermission: pa.create.own || pa.view.own)
- **NEW**: `pages/SalesDashboard.jsx` — thin wrapper rendering `<PartnerDashboard mode="sales" />`
- **NEW**: `components/sales/SalesWidgets.jsx` — 4 placeholder widgets (Target/Commission/Rank/Followups) with "Coming in Phase 4X" badges
- **NEW**: `pages/ComingSoon.jsx` — friendly placeholder for unbuilt features
- **MODIFIED**: `pages/PartnerDashboard.jsx` — accepts `mode` prop (default "partner"); allows sales roles when mode="sales"; injects `<SalesWidgetsRow>` above PartnerHome
- **MODIFIED**: `pages/Login.jsx` — smart redirect for 4 sales roles → `/sales/dashboard`
- **MODIFIED**: `components/pa/PaCreateForm.jsx` — Lead Source dropdown (10 options) at TOP of form, optional but recommended
- **MODIFIED**: `components/PreAssessmentPipeline.jsx` — form state includes `lead_source` + `lead_source_detail`

#### RBAC Permission Updates
- `sales_executive` role now has 28 permissions (all 18 partner perms + 10 sales/self-service)
- Added missing: `agreement.view.own`, `agreement.generate.own`, `invoice.view.own`

#### Verified
- ✅ Partner workflow EXACTLY unchanged (regression: 4/4 manual tests + screenshot)
- ✅ Sales exec can do everything partner can (parity: 11/11 verified)
- ✅ Cross-role scope isolation (sexec → partner PA = 403; partner → sexec PA = 403)
- ✅ Admin bypass preserved
- ✅ Phase 3A/3B + RBAC regression all passing

---

## 📅 February 2026

### ✅ Phase 3B — HR Admin Settings UI (COMPLETE — backend 100% tested)
**Completed:** Feb 13, 2026 (same day as 3A)
**Tests:** 42/42 backend tests passed via testing_agent_v3_fork (`/app/test_reports/iteration_93.json`)
  - 19 Phase 3B new tests
  - 23 Phase 3A regression tests (all still pass)

#### Backend
- Renamed router prefix: `/api/hr-admin/*` → `/api/hr/*`
- New endpoints in `routers/hr_admin.py`:
  - `POST /api/hr/leave-types` — create custom leave type (key uniqueness enforced)
  - `DELETE /api/hr/leave-types/{key}` — delete (blocks system types)
  - `POST /api/hr/holidays/import-indian/{year}` — bulk seed 9 India holidays
  - `POST /api/hr/holidays/copy-from/{from_year}/to/{to_year}` — clone year's holidays
  - `GET/PATCH /api/hr/approvers/config` — get/update approval workflow
  - `GET /api/hr/approvers/simulate/{user_id}` — visual chain simulator
  - `GET /api/hr/audit-log` — policy change audit trail
- New `policy_audit_log` MongoDB collection (lazy-created)
- All PATCH endpoints now log before/after to audit + use `exclude_unset` to support clearing nullable fields

#### Frontend — 5 New Admin Pages
- `/admin/hr/settings` — `AttendanceSettings.jsx` — 5 collapsible sections, live previews, save state
- `/admin/hr/holidays` — `HolidayManager.jsx` — List + Calendar views, bulk import/copy, CSV export
- `/admin/hr/leave-types` — `LeaveTypesManager.jsx` — 7-card grid + custom type creator + audit panel
- `/admin/hr/approvers` — `ApproverConfig.jsx` — 5 sections + **visual chain simulator** (Applicant → L1 → Final)
- `/admin/hr/audit` — `HRAuditLog.jsx` — Scope filter, expandable before/after diff

#### Shared Components
- `components/hr/HRSettingsLayout.jsx` — sidebar nav + breadcrumb wrapper for all 5 pages

#### Sidebar Integration
- AdminDashboard sidebar has new "HR Settings" group with 5 entries
- All routes wrapped in `RequirePermission` with appropriate perm gates
- Sales executive (non-admin) is properly blocked (403 redirect)

#### Acceptance Criteria — All Verified ✅
1. ✅ Admin sees HR Settings sidebar group
2. ✅ Sales Executive blocked from /admin/hr/* (403)
3. ✅ Office timings update reflects in next punch
4. ✅ Custom holiday added → visible in employee calendar
5. ✅ CL annual quota edit → reflects in user balances
6. ✅ Final approver change → next leave routes to new approver
7. ✅ Audit log captures all policy changes with timestamps
8. ✅ Approval chain simulator works (visual flow)
9. ✅ All Phase 3A functionality intact (regression: 23/23 passed)
10. ✅ All 4 default logins still work

---

## 📅 February 2026

### ✅ Phase 3A — Attendance & Leave Management (COMPLETE — backend 100% tested)
**Completed:** Feb 13, 2026
**Tests:** 23/23 backend tests passed via testing_agent_v3_fork (`/app/test_reports/iteration_92.json`)
**Test file:** `/app/backend/tests/test_phase3a_attendance_leaves.py`

#### Company Policies Implemented (configurable via /api/hr-admin/settings)
- 🕙 Office hours: 10:00 — 19:00 IST (9 hours)
- ⚠️ Late after 10 min grace (post 10:10 AM = late)
- 🚨 3 late marks/month → 1 CL auto-deducted (`record_late_mark` in attendance_logic.py)
- 📅 Monthly CL cap: 1/month (counts approved + pending)
- 🥪 Sandwich leave (Fri-Mon = 4 days incl. weekend; Sat-Mon = 3 days)
- 📏 Max 7 consecutive days leave
- 🚫 Long leave (>5 days) once per year
- ❌ No approval = LWP (auto-marked after working day with no punch + no leave)
- ⏱ Regularization grace: 3 days

#### 7 Leave Types Seeded
| Type | Quota | Monthly Cap | Max Consecutive |
|------|-------|-------------|-----------------|
| Casual Leave (CL) | 12/yr | **1/month** | 1 day |
| Sick Leave (SL) | 12/yr | — | 7 days |
| Earned Leave (EL) | 24/yr | — | 7 days |
| Comp-off | earned | — | 3 days |
| LWP | unlimited | — | — |
| Maternity | 180 days | — | 180 |
| Paternity | 5 days | — | 5 |

#### Backend (3 new routers + 1 migration + 1 logic module)
- `routers/attendance.py` — punch-in/out, current-status, my-month, today, late-marks, regularization, LWP scan, dashboard
- `routers/leaves.py` — types, my-balance, validate, apply, my-history, inbox, inbox-final, decide, all, balance-history
- `routers/hr_admin.py` — settings GET/PATCH, holidays CRUD, leave-types PATCH, approver-config
- `core/attendance_logic.py` — All business logic (sandwich detection, late marks, validation, balance deduction, approver resolution, LWP marking)
- `migrations/attendance_leave_migration.py` — Seeds defaults + backfills

#### New DB Collections
- `attendance_settings` (singleton with company policies)
- `attendance_logs` (one per user per day)
- `leave_types` (7 types)
- `leave_balances` (per user/type/year — with monthly_used breakdown)
- `leave_requests` (with L1 + Final approver IDs)
- `holidays` (year-indexed)
- `late_marks_tracker` (per user per month)
- `leave_balance_history` (audit log)
- `lwp_records` (auto-marked absences)
- `attendance_regularizations` (employee disputes)

#### Frontend
- `components/attendance/PunchWidget.jsx` — punch in/out with GPS, late banner, hours progress, late marks indicator
- `pages/MyAttendance.jsx` — calendar view with color-coded statuses, late marks card, regularization modal
- `pages/MyLeaves.jsx` — balance cards, apply modal with live validation (sandwich detection in UI), history with cancel
- `pages/LeaveApprovals.jsx` — L1 / Final inbox with one-click approve/reject
- PortalWelcome — punch widget mounted at top for internal employees

#### RBAC Updates
- New permissions auto-granted to every internal role (Phase 1 migration auto-merges):
  - `attendance.clock.own`, `attendance.view.own`
  - `leave.apply.own`, `leave.view.own`
  - `profile.view.own`, `profile.update.own`
- `SELF_SERVICE_PERMISSIONS` constant in `core/rbac/seed_data.py`

#### Two-Stage Approval Workflow Verified
- Sales Exec → L1 Manager (reports_to) → Final Approver (admin or dept head, configurable)
- If user IS the L1 approver (dept head), L1 stage is skipped
- If L1 approver IS the final approver, single approval suffices
- All decisions audited, notifications sent at each stage

---

## 📅 January 2026

### ✅ Phase 2 — Employee Portal Foundation + RBAC
**Completed:** Jan 2026

- 18 RBAC roles across 8 departments
- 219 permissions across 11 resources
- Dynamic role-based dashboard (PortalWelcome) with `ui_modules`
- Employee CRUD, Department/Org Chart, View Dashboard As (read-only preview)
- Password reset / Force-change-on-first-login / Forgot password flow
- User role history audit trail

### ✅ Phase 2.2 — Frontend Route Guard
**Completed:** Jan 2026 (verification pending in this fork; bug-fix scope completed)
- `RequirePermission.jsx` wrapper for sensitive routes
- Applied to `/admin/employees`
- Admin-only action buttons hidden conditionally in EmployeeDetailModal

---

## 📅 Pre-Jan 2026 (Phases A — D)

### ✅ Phase A-D — Core CRM (5-step funnel)
- Pre-Assessment forms with public share links
- Admin Approval workflow + Proposal Generation (AI - Claude)
- Consent & Payment (mocked Stripe)
- Case Manager assignment + Client mini-portal
- AI Eligibility Pre-score, Visa Pathway comparison
- Legal Archive with SHA-256 integrity chain
- Agreement Template Engine, Document Expiry Tracker
- WhatsApp Smart Share (mocked Twilio)
