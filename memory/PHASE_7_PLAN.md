# LEAMSS Phase 7 — Knowledge-Base-Driven Unified Sales Flow

> **Status:** PROPOSAL — Pending Sir's approval before any code is written.
> **Author:** E1 Agent (drafted from Sir's DOCX feedback + ANZSCO Excel + sample PDF)
> **Date:** May 24, 2026
> **Total scope:** 5 phases, ~17-22 working hours across 4-5 sessions.

---

## 📜 GUIDING PRINCIPLES (Sir's vision in 5 lines)

1. **Knowledge Base = Single Source of Truth.** Whatever admin updates in KB → reflects everywhere instantly. No isolated/duplicate data.
2. **One unified linear flow** — Country → Eligibility → Points → Code → Guide → Cost → Benefits → Services → Report → PA → Payment → Case.
3. **3-tier content gating** — Public Teaser → PA Paid (₹5,100) Full Report → Main Fees Paid Proposal.
4. **Premium "wow" design** — Justify ₹5,100+ price tag with branded, animated, professional output.
5. **No compromise on quality, no fragmentation.**

---

# 🔴 PHASE 7.1 — Knowledge Base Unification (FOUNDATION)

**Effort:** 6-8 hours · **Risk:** Low · **Dependencies:** None · **Blocks:** 7.2, 7.3, 7.4

## 🎯 Objective
Establish Knowledge Base as the single source of truth. Integrate Sir's Feb 2026 ANZSCO Excel (480 occupations × 8 official dimensions). Fix all broken inter-collection linkages. Add Protection Policy as a managed KB entity.

## ❌ Current Problems
- `occupation_master` (88 codes) ↔ `country_templates` (3 countries) ↔ `country_guides` (5 countries) are **3 disconnected silos**.
- Sir added "UK" Country Guide but `country_templates` doesn't have UK. **Pipeline broken.**
- Occupation Search "Sample Cases / Similar Codes / Skill Assessment" are partial-AI / hardcoded — **not KB-driven**.
- No salary, tasks, industries, state distribution per occupation (these go to Assessment Report).
- No "Custom Q&A" per code (Sir wants to add specific notes per occupation).
- "Protection Policy" — Sir's biggest USP — not managed anywhere.
- Country Guides has 7 fixed sections (Overview, PR Pathways, Eligibility, Fees, Timeline, Pros/Cons, Settlement) — Sir wants ability to add custom sections.

## ✅ Target State
- ONE unified KB schema where Occupation → Country Template → Country Guide are linked by `country_code`.
- 480 ANZSCO codes seeded with official Feb 2026 data (salary, tasks, industries, states, education, age).
- UK + USA country_templates added (parity with country_guides).
- Custom Q&A subdocument per occupation + per country.
- Protection Policy as a top-level KB entity (versioned, status-tracked).
- All "Verify" flows centralized — one dashboard, one workflow.

## 📂 Schema Changes

### 🆕 NEW Fields in `occupation_master` (additive, no migration)
```json
{
  "code": "261313",
  // existing fields stay
  // ─── NEW for Phase 7.1 ───
  "anzsco_profile": {                              // From Feb 2026 Excel
    "employed_count": 142500,
    "part_time_share_pct": 18,
    "female_share_pct": 22,
    "median_age": 36,
    "annual_employment_growth_pct": 4.2,
    "median_weekly_earnings_aud": 2150,
    "median_full_time_weekly_aud": 2400,
    "median_full_time_hourly_aud": 63.2,
    "full_time_share_pct": 82,
    "avg_full_time_hours_per_week": 42
  },
  "tasks": [                                        // From "Occupation Tasks" sheet
    "Designs, develops, tests, and maintains software systems...",
    "Researches user requirements...",
    // 8-15 task items per code
  ],
  "industries_ranked": [                            // From "Industries" sheet
    {"name": "Professional Services", "share_pct": 38},
    {"name": "Public Administration", "share_pct": 12},
    {"name": "Finance & Insurance", "share_pct": 11}
    // Top 5
  ],
  "state_distribution": {                           // From "States" sheet
    "NSW": 35, "VIC": 28, "QLD": 16,
    "WA": 9, "SA": 6, "ACT": 4, "TAS": 1, "NT": 1
  },
  "age_profile": {                                  // From "Age Profile" sheet
    "15_24": 8, "25_34": 32, "35_44": 31,
    "45_54": 18, "55_64": 9, "65_plus": 2
  },
  "education_distribution": {                       // From "Education" sheet
    "post_grad": 34, "bachelor": 45, "diploma": 12,
    "cert_3_4": 6, "year_12": 2, "year_11_or_less": 1
  },
  "custom_qa": [                                    // NEW — Sir asked
    {"question": "Is RPL accepted for ACS?", "answer": "Yes, with 5 yrs+ exp + AQF skills assessment...", "by": "admin_user_id", "at": "..."}
  ],
  "data_sources": [                                 // Audit trail
    {"label": "ABS ANZSCO Feb 2026", "url": "https://www.jobsandskills.gov.au/...", "imported_at": "..."}
  ]
}
```

### 🆕 NEW collection `protection_policies`
```json
{
  "id": "POL-2026-001",
  "policy_type": "skill_assessment_negative | visa_rejection",
  "title": "LEAMSS Protection Policy — 100% Refund on Negative Outcomes",
  "description_markdown": "We Value Emotions. India's first migration consultancy with...",
  "refund_terms": {
    "covers": ["professional_fees", "government_fees"],
    "excludes": ["english_test_fees", "medical_costs"],
    "claim_within_days": 90
  },
  "applicable_countries": ["AU", "CA", "NZ", "UK", "USA"],  // or ["*"] for all
  "applicable_visa_types": ["189", "190", "491", "EE", "PNP"],
  "version": "1.0",
  "status": "draft | verified | archived",
  "verification": {"by", "by_name", "at", "source_reference"},
  "created_at": "...",
  "updated_at": "..."
}
```

### 🆕 NEW Sections array in `country_guides` (replace fixed 7 sections with dynamic)
```json
{
  // existing fields stay
  "sections": [
    {"key": "overview", "title": "Country Overview", "body_markdown": "...", "is_default": true, "order": 1},
    {"key": "pr_pathways", "title": "PR Pathways", "body_markdown": "...", "is_default": true, "order": 2},
    // ...
    {"key": "salary_data", "title": "Salary by Code (Sir's custom)", "body_markdown": "{{auto-injected from occupation_master.anzsco_profile.median_weekly_earnings_aud}}", "is_custom": true, "order": 8}
  ]
}
```
Sir gets ability to add **custom sections** beyond the 7 defaults.

### 🔧 FIX existing `country_templates` — add UK, USA
Seed UK and USA templates as `draft` status with empty factors arrays. Admin will fill via existing UI.

### 🆕 Optional view collection `kb_verification_queue` (denormalized — fast read)
Or compute on-the-fly via `$unionWith` aggregation. Recommended: aggregation-only for now (zero migration).

## 🛠️ Backend Changes

### New endpoints
```
POST   /api/kb/import-anzsco-excel              (admin only, multipart upload)
         → Parses Excel, upserts 480 occupations with new fields
         → Returns: {imported, updated, skipped, errors[]}

GET    /api/protection-policies                  (list)
GET    /api/protection-policies/{id}
POST   /api/protection-policies                  (create)
PUT    /api/protection-policies/{id}
POST   /api/protection-policies/{id}/verify
GET    /api/protection-policies/public           (verified only, for client view)

GET    /api/occupation-master/{code}/full-profile
         → Returns occupation + linked country_template + linked country_guide
         → ONE call, joined data, ready for Assessment Report

GET    /api/kb/unified-status
         → Returns counts: total occupations, verified %, country templates verified, country guides verified, policies verified, items pending verification
```

### Modified endpoints
- `GET /api/occupation-master/{code}` — now returns anzsco_profile, tasks, etc.
- `GET /api/country-guides/public/{code}` — supports custom_sections + auto-injection from linked occupation
- `POST /api/country-templates/seed-defaults` — extends to UK + USA

### Migration script
`/app/backend/migrations/phase71_kb_unification.py`
- Idempotent
- Step 1: Add UK + USA country_templates (status=draft, empty factors)
- Step 2: Add `anzsco_profile`, `tasks`, `industries_ranked`, `state_distribution`, `age_profile`, `education_distribution`, `custom_qa`, `data_sources` fields to existing occupations (default empty)
- Step 3: Convert country_guides.sections from current fixed 7 → ordered array with is_default/is_custom flags (backwards compatible)
- Step 4: Create indexes: `(country_code, anzsco_profile.median_weekly_earnings_aud)` for salary range filtering

### Excel import service
`/app/backend/core/anzsco_excel_importer.py`
- Uses `openpyxl` (already installed)
- Maps each of Sir's 8 sheets to the respective subdocument field
- Validates ANZSCO code format
- Logs each row outcome
- Rate-limit safe (no external API calls)

## 🎨 Frontend Changes

### New pages
- `/admin/kb/anzsco-import` — Excel upload wizard (drag-drop → preview → confirm → progress bar → report)
- `/admin/protection-policies` — CRUD list + 3-panel editor (mirrors Country Guides admin pattern)
- `/admin/kb/verification-hub` — Single unified screen with 4 tabs: Occupations · Country Templates · Country Guides · Policies. Each tab shows pending items, bulk verify.

### Modified pages
- `/admin/country-guides` — add "+ Custom Section" button to sections tab (existing tabs stay)
- `/admin/kb/occupation-master` — Occupation editor adds "ANZSCO Profile" + "Tasks" + "Industries" + "Custom Q&A" tabs

### New components
- `<ANZSCOProfileCard>` — visual chart of salary, age, gender, state, education distribution
- `<CustomQAManager>` — add/edit/delete custom Q&A items per code
- `<VerificationStatusBadge>` — universal pill (draft / verified / outdated)

## 🧪 Testing Strategy
- Unit: `tests/test_phase71_kb_unification.py` (15-20 tests)
- Integration: Upload Excel → verify 480 codes have new fields populated
- E2E: Admin opens Verification Hub → sees combined counts → clicks pending occupation → verifies → counts update
- Regression: Existing 37/37 tests must still pass

## ✓ Acceptance Criteria
- [ ] 480 ANZSCO codes seeded with Feb 2026 official data
- [ ] UK + USA country_templates exist (draft state)
- [ ] Protection Policy can be created, edited, verified, published
- [ ] Custom Q&A works per occupation code
- [ ] Verification Hub shows unified counts across 4 entity types
- [ ] Zero regression in existing flows
- [ ] All updates from Verification Hub reflect in downstream report PDF (verified in Phase 7.3)

---

# 🔴 PHASE 7.2 — Unified Wizard + Cost Estimator

**Effort:** 5-6 hours · **Risk:** Medium (touches the most-used flow) · **Dependencies:** 7.1 · **Blocks:** 7.3

## 🎯 Objective
Replace 3 fragmented wizards (Smart Sales Helper / NEW Profiles / standalone Eligibility Calculator) with ONE unified wizard. Pull all data from verified Knowledge Base. Add Cost Estimator as a step.

## ❌ Current Problems
- 3 wizards with overlapping purpose → user confusion.
- Calculator engine ≠ Wizard engine — different code paths, inconsistent results.
- "I know profession" → AI helper trigger (not direct KB search).
- AI code suggestions source unclear — not from verified KB.
- Subclass select → only that subclass's points calculated (e.g. 190 selected → 491 not shown).
- After code selected → tasks, salary, fees do NOT auto-populate.
- No Cost Estimator step.

## ✅ Target State
- ONE wizard at `/sales/wizard` (8 steps):
  1. **Start** — Capture client name/email/phone OR pick existing client profile
  2. **Approach** — "I know profession" / "Help me suggest" / "Compare 2-3 codes"
  3. **Profile** — Personal, education, language, work experience (Infosheet auto-fills if client filled)
  4. **Code Selection** — KB-driven search (with AI co-pilot suggestion). Returns enriched code with tasks/salary preview.
  5. **Country & Subclasses** — Multi-select subclasses (189 + 190 + 491 simultaneously) for parallel comparison
  6. **Cost Estimator** — Editable cost breakdown (gov fees + body fees + LEAMSS professional fees + protection policy)
  7. **Review** — All data shown, AI suggestions panel, polish text
  8. **Done** — Generate Report + Share + Create PA (with 3-tier gating)
- Live calculator engine consistent across steps (single function `calculate_points()` used everywhere)
- Parallel subclass comparison table (189: 80 pts, 190: 85 pts, 491: 95 pts shown side-by-side)
- After code selection: all KB data auto-populates (tasks, salary, industries, state demand)

## 📂 Schema Changes

### Modify `sales_assessments`
Add fields:
```json
{
  // existing fields stay
  "subclass_comparisons": [                       // Phase 7.2 — parallel comparison
    {"subclass": "189", "total": 80, "breakdown": {...}, "eligible": true},
    {"subclass": "190", "total": 85, "breakdown": {...}, "eligible": true, "state_nomination_bonus": 5},
    {"subclass": "491", "total": 95, "breakdown": {...}, "eligible": true, "regional_bonus": 15}
  ],
  "cost_estimator": {                             // Phase 7.2 — editable
    "currency": "INR",
    "items": [
      {"category": "Government Fees", "label": "Visa Application 189", "amount": 430000, "is_estimated": true, "kb_source": "country_template:AU:189"},
      {"category": "Skill Assessment", "label": "ACS", "amount": 50000, "is_estimated": true, "kb_source": "skill_body_master:ACS"},
      {"category": "LEAMSS Professional Fees", "label": "End-to-end PR processing", "amount": 195000, "is_editable": true},
      {"category": "Protection Policy Coverage", "label": "100% refund on negative outcome", "amount": 0, "kb_source": "protection_policy:POL-2026-001"}
    ],
    "total_inr": 675000,
    "notes": "Quoted on 24-May-2026, valid for 30 days",
    "approved_by_admin": false
  },
  "infosheet_link": "INFO-...",                   // optional link to client infosheet
  "wizard_version": "v2_phase71"                  // for analytics
}
```

### Delete (with backup) collections
- `eligibility_profiles` (orphan parallel collection) — archive to `_archived_eligibility_profiles_backup` then delete

## 🛠️ Backend Changes

### New endpoints
```
POST   /api/sales/wizard/v2/save-step           (per-step save, debounced)
POST   /api/sales/wizard/v2/calculate-parallel  (multi-subclass points calc)
GET    /api/sales/wizard/v2/cost-estimator/defaults?country={code}&subclass={code}
         → Returns suggested cost items from KB
POST   /api/sales/wizard/v2/finalize             (writes sales_assessments)
```

### New unified calculator service
`/app/backend/core/unified_calculator.py`
- Single `calculate_points(profile, country, subclass)` function
- Used by both old eligibility-calculator endpoint (kept for backwards compat) and new wizard
- Pulls factor definitions from verified `country_templates`
- Returns: `{total, breakdown[], eligible, pass_mark, recommendations[]}`

### Deprecated endpoints (kept for 1 month, returns 410 Gone after)
- `/api/eligibility/calculate-standalone` → redirect to `/api/sales/wizard/v2/calculate-parallel`
- `/api/new-profiles/*` → archive routes

## 🎨 Frontend Changes

### New unified wizard
`/app/frontend/src/pages/sales/UnifiedWizardV2/`
```
├── index.jsx                  (state machine, navigation)
├── steps/
│   ├── Step1Start.jsx
│   ├── Step2Approach.jsx
│   ├── Step3Profile.jsx
│   ├── Step4CodeSelection.jsx (KB-driven search + AI co-pilot drawer)
│   ├── Step5CountrySubclasses.jsx (multi-select, parallel calc)
│   ├── Step6CostEstimator.jsx
│   ├── Step7Review.jsx
│   └── Step8Done.jsx          (Generate Report + Share + Create PA)
├── components/
│   ├── CodeSearchKB.jsx       (search with KB filter)
│   ├── AICoPilotDrawer.jsx
│   ├── ParallelSubclassTable.jsx
│   └── CostEstimatorEditor.jsx
└── lib/
    ├── wizardState.js          (zustand or context)
    └── calculator.js            (calls /api/sales/wizard/v2/calculate-parallel)
```

### Deleted pages (with rollback safety)
- `/sales/client-assessment` (old wizard) → 301 redirect to `/sales/wizard`
- `/sales/eligibility-calculator` (standalone) → 301 redirect to `/sales/wizard?step=5`
- `/sales/new-profile` → 301 redirect to `/sales/wizard`

### Modified pages
- `/sales/my-assessments` — add "Continue Wizard" button on each row for in-progress drafts
- `/admin/dashboard` — sidebar item "New Sales Assessment" → /sales/wizard

## 🧪 Testing Strategy
- Unit: `tests/test_phase72_unified_wizard.py` (12-15 tests)
- E2E: Walk through all 8 steps, verify Cost Estimator persists, verify subclass comparison renders, verify Generate Report at step 8 works
- Regression: Old wizard redirects work, no broken links

## ✓ Acceptance Criteria
- [ ] Single wizard handles all 3 prior flows
- [ ] Calculator and wizard show identical points for same input
- [ ] Parallel subclass comparison shows 189+190+491 simultaneously
- [ ] After code selection, salary/tasks/state demand visible in wizard
- [ ] Cost Estimator items pre-fill from KB defaults
- [ ] Cost Estimator total is editable + persists
- [ ] Old wizard URLs 301 redirect to new wizard (no 404s)

---

# 🔴 PHASE 7.3 — Premium Assessment Report v2

**Effort:** 4-5 hours · **Risk:** Medium (PDF rendering complexity) · **Dependencies:** 7.1 + 7.2 · **Blocks:** None

## 🎯 Objective
Rebuild Assessment Report PDF to "wow" level. Inject all KB data (salary, tasks, state demand, protection policy). Implement 3-tier content gating. Optional: AI/template editor for Sir to update designs.

## ❌ Current Problems
- "Design colour combination acha nahi" — Sir's words
- Task descriptions blank
- Fees & Costs has process but **no amounts**
- No salary/state/industry data
- No Protection Policy section
- 3-tier gating not implemented at PDF level (only UI)
- Static layout — Sir wants ability to refresh design over time

## ✅ Target State
- **Cover page** — animated SVG (gradient + brand mark + client name + score badge)
- **Section 1: Executive Summary** — country comparison table with verdicts
- **Section 2: Client Profile** — Infosheet-driven, photo if present
- **Section 3: Selected Occupation Deep-Dive** — KB-driven:
  - ANZSCO code + title + skill level
  - Tasks (bulleted, from Feb 2026 Excel)
  - Salary (median weekly + hourly, from Excel)
  - State demand (visual horizontal bar chart per state)
  - Industries (top 5 with %)
  - Age profile + Education distribution (mini charts)
- **Section 4: Points Breakdown** — per-subclass (189/190/491) parallel table
- **Section 5: Country Guide** — verified content from KB (already wired in Phase 6.10.3 fix)
- **Section 6: Cost & Investment Breakdown** — Cost Estimator data (from wizard step 6) — itemized with amounts, currency, validity
- **Section 7: Process & Timeline** — visual timeline with stages
- **Section 8: 🛡️ Protection Policy** — Sir's USP — full page with promise, what's covered, what's not, claim process
- **Section 9: LEAMSS Services & Why Us** — bullet of services + brand story
- **Section 10: Next Steps & PA Payment** — clear CTA + payment link
- **Disclaimer + Footer with snapshot ID + integrity hash**

### 3-Tier Content Gating
| Tier | Trigger | What Client Sees |
|---|---|---|
| **Tier 1 — Teaser** | Public link before PA payment | Cover + Section 1 + 2 + 8 + 10 (5 pages) |
| **Tier 2 — Full** | PA paid (₹5,100) | All 10 sections (15-20 pages) |
| **Tier 3 — Proposal** | After Tier 2 + Main Fees | Cover updates to "Proposal & Engagement Letter" with signed e-agreement |

## 📂 Schema Changes
None — purely renderer change. Existing `report_snapshots` collection used.

### Modify report snapshot to capture tier
```json
{
  // existing fields
  "render_tier": "teaser | full | proposal",      // Phase 7.3
  "gating_state": {
    "pa_payment_verified": false,
    "main_fees_paid": false
  }
}
```

## 🛠️ Backend Changes

### Modified renderer
`/app/backend/core/report_renderer_v2.py` (new file, keeps v1 as fallback)
- New section functions: `_section_anzsco_profile()`, `_section_cost_estimator()`, `_section_protection_policy()`, `_section_services()`, `_section_next_steps()`
- Animated SVG cover via `reportlab.graphics.renderPDF` (transparent gradient + brand mark)
- Tier-aware: receives `render_tier` and skips sections accordingly
- Premium typography (Manrope headings, Public Sans body — already in /app/frontend, install for backend too)

### New endpoints
```
GET    /api/assessment-reports/{snapshot_id}/pdf?tier=teaser|full|proposal
         → Authorization-aware: client gets teaser by default, full only if PA paid
POST   /api/assessment-reports/{snapshot_id}/upgrade-to-full
         → Triggered by payment webhook (or admin override)
```

### Charts rendering (for state demand, age, industries)
Use `reportlab.graphics.charts` (built-in) or pre-render to SVG → embed.

## 🎨 Frontend Changes

### Public Report Viewer
`/app/frontend/src/pages/PublicReportView.jsx` — already exists, just:
- Add "Tier 1 / Tier 2 / Tier 3" indicator badge
- Show "Pay ₹5,100 to unlock full report" CTA when in Tier 1
- Stripe checkout integration (or mock for now)

### Optional: Template Editor (Sir's "Canva-style" request)
`/admin/report-template-editor` — future enhancement, **NOT in Phase 7.3 v1 scope**. Add to Phase 7.6 backlog.

## 🧪 Testing Strategy
- Unit: `tests/test_phase73_premium_report.py` (8-10 tests)
- Visual regression: Generate sample PDF, AI vision compare against design spec
- Integration: Client view tier 1 → pay PA → upgrade to tier 2 → verify PDF rebuilds with full sections

## ✓ Acceptance Criteria
- [ ] Cover page has animated/gradient design (no plain blue rectangle)
- [ ] Tasks list visible per occupation (from Feb 2026 Excel data)
- [ ] Salary, state demand, industries with amounts/percentages
- [ ] Cost Estimator section with itemized amounts (not blank)
- [ ] Protection Policy full page with refund terms
- [ ] Tier 1 PDF ≤ 5 pages, Tier 2 PDF 15-20 pages
- [ ] Sir says "wow" after seeing first generated PDF (subjective but critical)

---

# 🟡 PHASE 7.4 — Profile Merge + Infosheet Integration

**Effort:** 2-3 hours · **Risk:** Low · **Dependencies:** 7.2 · **Blocks:** None

## 🎯 Objective
Eliminate duplication: NEW Profiles, Client Profile sub-features. Merge into Client Assessment. Embed Infosheet send/track in wizard.

## ❌ Current Problems
- NEW Profiles is a parallel mini-wizard that redirects to Smart Sales Helper (dead-end loop)
- Client Profile data ≠ Saved Assessment data (two different collections)
- Sales Helper sub-tab inside Client Profile is duplicate / useless
- Infosheet feature is isolated — not integrated with wizard

## ✅ Target State
- ONE client entity (`clients` collection). Sales assessments reference it.
- ONE assessment entity (`sales_assessments`). Auto-creates `clients` record on wizard step 1.
- NEW Profiles deleted (its only useful feature — AI code suggestion from resume — folded into Wizard Step 4)
- Client Profile sub-tabs simplified to: Overview · Assessments · Documents · Infosheets · Activity
- "Send Infosheet" button inside wizard Step 3 → client gets magic link → fills form → wizard step 3 auto-populates

## 📂 Schema Changes

### NEW collection `clients` (replaces fragmented client data)
```json
{
  "client_id": "CLI-2026-00012",
  "name": "Ravi Kumar Sharma",
  "email": "ravi@example.com",
  "phone": "+91-9876543210",
  "country_of_origin": "IN",
  "current_location": "Mumbai",
  "preferred_destinations": ["AU", "CA"],
  "infosheet_status": "not_sent | sent | partial | completed",
  "infosheet_completed_at": "...",
  "linked_assessment_ids": ["SAH-..."],
  "linked_pa_ids": ["PA-..."],
  "linked_case_ids": ["CASE-..."],
  "consent": {"version", "signed_at", "ip", "user_agent"},
  "created_at": "...",
  "created_by": "user_id",
  "updated_at": "..."
}
```

### Migration
- Walk all `sales_assessments` → create `clients` record from snapshot data
- Walk all `pre_assessments` → link or create `clients`
- Walk all infosheets → link to `clients`
- Old collections kept until 30-day verification window

## 🛠️ Backend Changes

### New endpoints
```
GET    /api/clients
GET    /api/clients/{id}
POST   /api/clients
PUT    /api/clients/{id}
GET    /api/clients/{id}/timeline   (cross-collection activity log)
POST   /api/clients/{id}/send-infosheet
```

### Modified
- `POST /api/sales/wizard/v2/save-step` for step 1 → upserts `clients` record (find_or_create by phone+email)

## 🎨 Frontend Changes

### New pages
- `/clients` — list view
- `/clients/{id}` — 5-tab profile (Overview · Assessments · Documents · Infosheets · Activity)

### Deleted (with redirects)
- `/sales/new-profile` → /clients/new
- `/client-profiles/*` (old) → /clients/*

## ✓ Acceptance Criteria
- [ ] One unified client record per (phone+email)
- [ ] Infosheet send button works inside wizard
- [ ] Filling infosheet auto-fills wizard fields
- [ ] No NEW Profiles page (deleted)
- [ ] Old client profile URLs 301 redirect

---

# 🟢 PHASE 7.5 — Cockpit + Verify Hub (FINAL POLISH)

**Effort:** 3-4 hours · **Risk:** Low · **Dependencies:** 7.1, 7.2, 7.3, 7.4

## 🎯 Objective
Layer the Pipeline Cockpit (mockup already approved-in-progress) on top of the now-solid foundation. Unified Verify Hub for KB management.

## What we'll do
- Wire the Cockpit mockup to real data via `/api/cockpit/pipeline` aggregation
- Make `/cockpit` the default landing for all roles
- Build `/admin/verify-hub` (4 tabs: Occupations · Templates · Guides · Policies)
- Delete `/sales/my-assessments` (replaced by Cockpit Assessments filter)

## ✓ Acceptance Criteria
- [ ] Cockpit shows real pipeline data from all 4 source collections
- [ ] Drill-in drawer wires to existing endpoints (no duplication)
- [ ] Verify Hub bulk-verify works
- [ ] All previous Phase 7.1-7.4 features accessible from Cockpit

---

# 📊 DATA FLOW DIAGRAM (Phase 7 end-state)

```
┌────────────────────────────────────────────────────────────────────┐
│                  KNOWLEDGE BASE ADMIN (Source of Truth)           │
│  ┌────────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ Occupation │  │   Country    │  │  Country   │  │Protection │ │
│  │   Master   │←→│  Templates   │←→│   Guides   │  │  Policies │ │
│  │  (480 KB)  │  │ (5 countries)│  │(5 countries)│  │           │ │
│  └─────┬──────┘  └──────┬───────┘  └─────┬──────┘  └─────┬─────┘ │
└────────┼────────────────┼─────────────────┼──────────────┼───────┘
         │                │                 │              │
         ↓ (KB-driven, verified data only)                 │
┌────────────────────────────────────────────────────────────────┐
│                     UNIFIED WIZARD V2                          │
│   Step 1: Start  →  Step 2: Approach  →  Step 3: Profile      │
│   Step 4: Code (KB search)  →  Step 5: Country+Subclasses    │
│   Step 6: Cost Estimator  →  Step 7: Review  →  Step 8: Done │
└──────────────────────────────┬─────────────────────────────────┘
                               ↓
              ┌────────────────┴──────────────────┐
              │   PREMIUM ASSESSMENT REPORT v2    │
              │  Tier 1 → Tier 2 → Tier 3 gated   │
              └─────────────────┬─────────────────┘
                                ↓
        ┌───────────────────────┴──────────────────────┐
        │   Public Share → PA Created → PA Paid →     │
        │   Proposal Sent → Main Fees → Case Active   │
        └──────────────────────────────────────────────┘
                                ↓
        ┌──────────────────────────────────────────────┐
        │            PIPELINE COCKPIT (visual)         │
        │  Leads · Assessments · PAs · Proposals · Cases  │
        └──────────────────────────────────────────────┘
```

---

# ⚠️ RISKS & MITIGATIONS

| Risk | Mitigation |
|---|---|
| Excel import has dirty data | Validation layer + manual review pass + dry-run mode |
| Old wizard URLs break (404s) | 301 redirects + analytics tracking |
| PDF render breaks for legacy snapshots | Keep `report_renderer.py` (v1) for old snapshots, route by `wizard_version` field |
| Migration corrupts production data | All migrations idempotent + dry-run flag + backup collections |
| Sir doesn't like new PDF design | Build v1, iterate based on feedback (build → review → polish cycle) |
| Cost Estimator complexity confuses sales | Provide KB defaults + 1-click "Use Default" + show only when admin enables |

---

# ⏱️ EFFORT BREAKDOWN

| Phase | Backend | Frontend | Migration | Tests | Total |
|---|---|---|---|---|---|
| 7.1 KB Unification | 3 hr | 2 hr | 1 hr | 1 hr | **7 hr** |
| 7.2 Unified Wizard | 2 hr | 2.5 hr | 0.5 hr | 1 hr | **6 hr** |
| 7.3 Premium Report | 2.5 hr | 0.5 hr | 0 hr | 1 hr | **4 hr** |
| 7.4 Profile Merge | 1.5 hr | 1 hr | 1 hr | 0.5 hr | **4 hr** |
| 7.5 Cockpit + Verify Hub | 1 hr | 2 hr | 0 hr | 0.5 hr | **3.5 hr** |
| **TOTAL** | 10 hr | 8 hr | 2.5 hr | 4 hr | **24.5 hr** |

---

# 🚀 RECOMMENDED SEQUENCING

**Option A — Foundation First (RECOMMENDED)**
- Day 1: Phase 7.1 (KB Unification + Excel Import) → Sir verifies via Verification Hub
- Day 2: Phase 7.2 (Unified Wizard) → Sir tests new wizard end-to-end
- Day 3: Phase 7.3 (Premium Report) → Sir sees "wow" PDF
- Day 4: Phase 7.4 (Profile Merge) → Cleanup loose ends
- Day 5: Phase 7.5 (Cockpit + Verify Hub) → Final polish

**Option B — Quick Win First**
- Day 1: Phase 7.3 with mock data → Sir sees "wow" PDF immediately
- Day 2: Phase 7.1 → Replace mock with real KB
- Day 3+: 7.2, 7.4, 7.5

**Option C — Sprint Mode (parallel risks)**
- Combine 7.1 + 7.2 backend together → 7.3 + 7.4 frontend → 7.5 polish
- Higher risk but compresses to 3 days

---

# 🎯 SUCCESS METRICS (post-Phase 7)

| Metric | Today | Phase 7 Target |
|---|---|---|
| Wizards in production | 3 | 1 |
| KB-disconnected fields in report | 6 | 0 |
| ANZSCO codes with full profile | 88 (basic) | 480 (Feb 2026 official) |
| Protection Policy visibility | 0% | 100% (every report) |
| Cost Estimator amounts in report | Blank | Itemized with totals |
| 3-tier gating | UI only | Backend + PDF enforced |
| Average partner page-jumps per client | 5-7 | 1 (Cockpit) |
| "Wow" reaction from Sir on first PDF | ❌ | ✅ |

---

# 📞 OPEN QUESTIONS FOR SIR

1. **Excel data sourcing** — Sir uploaded Feb 2026 Excel. Will Sir provide similar official data for CA (NOC), NZ (ANZSCO 6-digit), UK (SOC), USA (SOC)? If not, Phase 7.1 ships AU-rich, other countries with KB structure ready but data sparse.

2. **Cost Estimator authority** — Who can edit costs:
   - (a) Admin only sets all baseline + sales can adjust LEAMSS fees only
   - (b) Sales/partner can edit everything but admin must approve before sending
   - (c) Sales can edit any time, no approval gate

3. **Protection Policy versions** — Is there ONE policy or MULTIPLE (e.g., different policies per visa type or country)?

4. **Premium PDF design preference** — Sir wants "wow / animated". Options:
   - (a) Conservative premium (clean typography + branded headers + gradient covers)
   - (b) Editorial magazine style (full-bleed photos + pull quotes + multi-column)
   - (c) Tech-modern (dark sections + electric blue accents + data visualizations)

5. **Sir's Canva-style design editor** — Phase 7.6 backlog or now?

6. **Stripe integration timing** — Real payments for PA fee gating? Or mock until Phase 8?

---

# ✋ STATUS: AWAITING SIR'S APPROVAL

**Sir please review and tell me:**
1. Which option (A / B / C) for sequencing?
2. Answers to open questions 1-6 above?
3. Any phase to skip / add / modify?

**Once approved, I'll start Phase 7.1 first session.**
