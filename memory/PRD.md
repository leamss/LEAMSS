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

### Latest: Automated Government Fee Calculator (v1)
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
