# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client.

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
