# LEAMSS - Immigration Portal PRD

## Original Problem Statement
Multi-role immigration portal with React + FastAPI + MongoDB. Roles: Admin, Case Manager, Partner, Client.

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

### Latest: Phase A Retouch + 3 Major Features (2026-04-22)
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
