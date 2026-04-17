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

### Latest: Fee Database CRUD + Per-Estimate Edits (v3, 2026-04-17)
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
