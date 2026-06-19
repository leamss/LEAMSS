# 🔍 Phase 20 — Discovery Audit Report (Jun 19, 2026)
**Mode:** READ-ONLY · No code changes · Awaiting Sir's approval before Phase 20.1 starts

Sir 🙏, complete audit ho gaya. Yahaan section-wise findings hain. **Aapko surprise hone wala hai — bahut zyada already-built infrastructure exist karta hai jise hum upgrade kar sakte hain (NOT recreate).**

---

## 🅐 AI Workflow Builder

| Aspect | Current State | Status |
|---|---|---|
| **Route** | `/admin/ai-workflow-builder` (frontend) | ✅ Live |
| **Frontend file** | `frontend/src/pages/AIWorkflowBuilder.jsx` (876 lines) | ✅ Working |
| **Backend file** | `backend/routers/ai_workflow_builder.py` (610 lines) | ✅ Working |
| **LLM Integration** | `emergentintegrations.llm.chat.LlmChat` via `EMERGENT_LLM_KEY` env var | ✅ Wired |
| **Model used** | `_call_gpt()` — claims "GPT-5.2" in docstring but **NO model param passed** → defaults to whatever LlmChat picks | ⚠️ Defaults; should explicitly set model |
| **AI service unavailable error** | Line 503: `raise HTTPException(500, detail="AI service unavailable. Please try a verified template or top up your AI balance...")` — triggers when `_call_gpt` raises (budget/timeout/network). **I tested live and it actually returned a full Australia PR workflow successfully** — Sir's earlier hit was likely a transient budget issue or model timeout. Current key is funded ✓ | ⚠️ Race-prone — needs explicit Claude Sonnet 4.5 wiring + better fallback |
| **Verified Templates** | **10 templates** (Sir said 8 — actually 10) live in `step_documents.py` `_find_best_template()` keyword matcher. Templates: Canada PR Express Entry · Australia PR Skilled · Canada Visitor · Australia Tourist · UK Standard Visitor · NZ Visitor · USA B1/B2 · Singapore Tourist · UAE Tourist · UAE Golden Visa 10yr | ✅ Live |
| **Supported countries** | **51 countries** in `COUNTRY_REFERENCES` + country picker. Argentina, AU, Austria, Bahrain, Belgium, Brazil, CA, Chile, China, Colombia, Costa Rica, CZ, DK, Egypt, FI, FR, DE, GR, HK, IN, ID, IE, IT, JP, KE, MY, MU, MX, NL, **NZ, NG, NO, OM, PA, PH, PL, PT, QA, SA, SG, ZA, KR, ES, SE, CH, TH, TR, UAE, UK, USA, VN** | ✅ Far beyond 13 |
| **Visa categories per country** | Variable: AU has 5 (pr/visitor/student/work/partner), Canada 4 (pr/visitor/student/work), UK 4, NZ 4, USA 3, etc. **Total ~150+ visa-category combos** | ✅ Rich |
| **Source URLs in prompt** | Hardcoded in `COUNTRY_REFERENCES` dict: `ircc.canada.ca`, `homeaffairs.gov.au`, `gov.uk`, `immigration.govt.nz`, etc — **only `.gov` official sites; NO VFSglobal yet** | ⚠️ Sir wants VFSglobal added |
| **Output schema** | `{product_name, description, category, estimated_total_duration_days, estimated_government_fees, success_tips[], common_rejection_reasons[], steps:[{step_name, step_order, description, duration_days, required_documents:[{name, description, mandatory, typical_validity_days}], important_notes, government_fees}]}` | ✅ Strong |
| **"Verify" button** | `verified` state in frontend; checkbox "I have verified this information"; **does NOT currently persist `verified=true` to DB**. The Save button writes to `products` collection but the verified flag is lost on reload | ❌ **Missing persistence** |

### Gap analysis A
- 🔴 **VFSglobal source** not in prompt — add per Sir's directive
- 🔴 **Verified flag persistence** missing in products collection
- 🟡 **Explicit Claude Sonnet model** routing absent — relies on LlmChat default
- 🟡 **"Skill Assessment for AU+NZ only"** rule — currently AU PR + NZ PR both reference skills assessment in prompt, but the rule is NOT enforced as a schema constraint
- 🟢 51 countries + 10 templates is **strong baseline** — no need to "create from scratch"

---

## 🅑 Product Master

| Aspect | Current State | Status |
|---|---|---|
| **Collection** | `products` (19 docs — 7 real + 11 TEST_ from QA + 1 duplicate) | ✅ Live |
| **Routers** | `backend/routers/products.py` (276 lines) + `product_cost_structures.py` | ✅ Working |
| **Frontend** | `frontend/src/pages/admin/ProductsManager.jsx` | ✅ Live |
| **Schema** | `{id, name, description, category, country, visa_type, base_fee, service_price, commission_rate, commission_type, commission_tiers, commission_effective_from, cost_allocations, success_bonuses, computed, status, created_at, updated_at}` | ✅ Rich |
| **Categories** | Currently: `immigration`, `visa`, `work`, `test` (free-form) — Sir's directive needs `pre_assessment`, `skill_assessment`, `visa_workflow`, `nomination`, `english_test`, etc | ⚠️ Free-form; needs enum |
| **Commission infrastructure** | `commission_rate`, `commission_type` (percentage/flat), `commission_tiers[]` (volume-based), `effective_from`, `success_bonuses[]` per vendor — **VERY mature** | ✅ Excellent |
| **Cost allocations** | `cost_allocations[]` (per-vendor split with vendor_category, share %) — already wired in computed preview endpoint | ✅ Excellent |
| **`partner_product_commissions`** collection | 1 doc — partner-specific commission overrides | ✅ Live |
| **"Pre-Assessment toggle" field** | ❌ Does NOT exist — needs adding | ❌ MISSING |
| **AI Workflow → Product link** | `POST /api/ai-workflow/save` creates a product but does NOT store `workflow_id` back-ref (line 557) — verified: 0/19 products have `workflow_id` | ⚠️ Loose coupling |
| **RBAC** | Admin only for write (line 67, 107, 149). Read open to all authed users. | ✅ Correct |

### Gap analysis B
- 🔴 **`is_pre_assessment` flag** to mark a product as "this is a Pre-Assessment offering" — needs adding
- 🔴 **`workflow_id` back-ref** for AI-generated products
- 🔴 **`visa_subclass`, `assessing_body_code`** structured fields — currently `visa_type` is free-text
- 🟡 **Category enum + Indian-friendly groupings** — currently free-form
- 🟢 Commission + cost structure is **production-grade** — DO NOT touch
- 🟡 **11 TEST_ products clutter** — should soft-delete (not destructive)

---

## 🅒 Pre-Assessment + Mini Client Portal

| Aspect | Current State | Status |
|---|---|---|
| **Pre-Assessment router** | `backend/routers/pre_assessment.py` | ✅ Live |
| **Mini Portal router** | `backend/routers/pre_assess_portal.py` (full public link + OTP + magic login + partner preview flow) | ✅ Live |
| **Collection** | `pre_assessments` (33 docs), `pre_assessment_documents` (13 docs) | ✅ Live |
| **🚨 Fee — Sir's Q2 concern CONFIRMED** | `PRE_ASSESSMENT_FEE = 5100` HARDCODED at `pre_assessment.py:58` (INR). Used in `create`, `send-payment-link` (Stripe checkout amount), and stored in `pa_fees_amount` field. | 🔴 **MUST FIX — needs to read from product** |
| **Stripe integration** | `emergentintegrations.payments.stripe.checkout.StripeCheckout` — **LIVE wired** with webhook at `/api/webhook/stripe`, currency=INR, dynamic redirect URLs | ✅ Live |
| **Mock payment endpoint** | `POST /{pa_id}/mock-payment` — exists for testing without Stripe | ✅ Useful |
| **Payment link** | `POST /{pa_id}/send-payment-link` creates Stripe session, returns checkout URL, logs activity | ✅ Live |
| **Public client link flow** | `pre_assess_portal.py` (681 lines): generate-public-link → public/{token} view → public/mock-pay → auto-creates Client user with random password → temp credentials emailed (mock) | ✅ Comprehensive |
| **OTP login** | `/otp/request` + `/otp/verify` (hashed) | ✅ Live |
| **Magic login** | `/magic-login` | ✅ Live |
| **Doc upload** | `POST /{pa_id}/upload-document` + `GET /{pa_id}/documents` | ✅ Live |
| **Client submit for review** | `POST /client/submit/{pa_id}` | ✅ Live |
| **Status flow** | `created → payment_pending → payment_received → documents_submitted → partner_review → under_review → completed/rejected` | ✅ Documented |
| **Admin override (password reset, lock)** | Not directly inspected — need deeper check (skipped to keep audit fast) | 🟡 TBD |

### Gap analysis C
- 🔴 **Fee → product link**: Replace `PRE_ASSESSMENT_FEE = 5100` with `pa.product_id → products.base_fee` lookup
- 🔴 **Per country/visa fee variation**: Sir wants different PA fees for different products (e.g. AU PR PA = ₹15K, USA B1/B2 PA = ₹3K)
- 🟢 Stripe live, mock pay exists, public link + OTP + magic login all there — **MASSIVE existing infra**
- 🟡 **Coupon collection** — does NOT exist; needs creating if Sir wants discounts
- 🟡 **Admin override** (password reset, lock account) — needs explicit endpoint audit

---

## 🅓 Info Sheet

| Aspect | Current State | Status |
|---|---|---|
| **Existing module** | `backend/routers/eligibility_info_sheet.py` (Phase 6.7 Part 2 — public link self-fill workflow) | ✅ Live |
| **Frontend editor** | `frontend/src/components/InfoSheetEditor.jsx` — embedded in case detail page; product-aware schema | ✅ Live |
| **Public fill page** | `frontend/src/pages/eligibility/PublicInfoSheet.jsx` (383 lines) — token-based, no login | ✅ Live |
| **Current schema (top-level keys)** | `case_id, client_id, full_name, date_of_birth, nationality, passport_number, marital_status, current_profession, designation, years_experience_total, industry, change_history, status` etc — **3 docs in `information_sheets` collection** | ⚠️ **Much thinner than Sir's docx spec** |
| **Resume Upload + AI extract** | `POST /api/eligibility/profiles/resume-extract` — `core/resume_extractor.py` uses **Claude Sonnet 4.6 via emergentintegrations** for PDF/DOCX parsing. **LIVE.** Result fills profile fields. | ✅ EXCELLENT (already exists!) |
| **Audit trail** | `change_history`, `changes_summary`, `updated_by_role` already tracked | ✅ Live |
| **Sections** | Current schema NOT structured as 6 sections (Personal/Family/Migrating Deps/Qualifications/Employment/Resume) — currently flat field set | ❌ Needs restructuring |

### Gap analysis D
- 🔴 **Sir's 6-section schema** (Personal · Family Chart · Migrating Dependents Table · Relevant Qualifications · Employment · Resume Upload) — **needs migrating existing flat schema to sectioned schema**
- 🔴 **Family Chart dynamic multi-entry** — not currently in schema
- 🔴 **Migrating Dependents multi-row** — not currently in schema
- 🔴 **Multi-entry Qualifications + Employment** — currently single-entry
- 🟢 **Resume → AI extract already wired** via Claude Sonnet 4.6 → can auto-fill new schema with one wrapper update
- 🟢 **Public-link self-fill workflow exists** — can reuse 100%

---

## 🅔 Proposal Generator + PDF Flow

| Aspect | Current State | Status |
|---|---|---|
| **AI Proposal router** | `backend/routers/ai_proposal.py` — `POST /api/ai-proposal/generate` | ✅ Live |
| **Proposal docs router** | `backend/routers/proposal_docs.py` — Proposal PDF + Invoice PDF + Esign + Send Invoice email | ✅ Live |
| **Phase 19.11 PDF** | `backend/routers/pre_assessment_report_v2.py` — **shipped 25 min ago!** WeasyPrint 8-section PDF | ✅ Just shipped |
| **PaProposalForm.jsx** | Frontend component exists | ✅ Live |
| **Esign integration** | `POST /{pa_id}/esign` saves signature | ✅ Live |
| **Send Invoice email** | `POST /{pa_id}/send-invoice` | ✅ Live |
| **Cross-link**: Pre-Assessment Report (Phase 19.11) ↔ Admin Review ↔ Proposal ↔ Client Portal | Each piece exists but **NOT yet stitched as single funnel** | 🟡 Stitching pending |

### Gap analysis E
- 🟢 **All building blocks exist**
- 🔴 **Funnel stitching**: Sales generates Phase 19.11 Pre-Assessment Report → Admin reviews + edits → Generates Proposal PDF → Sends to client portal → Client e-signs → Stripe payment → Mini portal provisioned. This linear funnel is **partially wired but no single dashboard tracking the lifecycle**

---

## 🅕 Brand Colors

| Aspect | Current State | Status |
|---|---|---|
| **CSS file** | `frontend/src/index.css` lines 22-66 | ✅ Found |
| **Brand variables** | `--leamss-orange: #f7620b` · `--leamss-teal: #2a777a` · `--leamss-red: #d81f26` | ✅ **ALREADY MATCHES SIR'S DIRECTIVE** |
| **Shadcn mapping** | `--primary: 178 49% 32%` (teal) · `--secondary: 22 93% 51%` (orange) · `--accent: 22 93% 51%` (orange) · `--destructive: 357 77% 48%` (red) | ✅ HSL conversions correct |
| **Background** | `--background: 210 20% 97%` = near-white slate ✅ matches "white background" | ✅ Correct |
| **Font** | `Public Sans` (body) + `Manrope` (headings) — already imported | ✅ Modern |
| **Dark mode** | Inverted teal/orange palette (lines 48-65) | ✅ Exists |

### Gap analysis F
- 🟢 **Brand colors ALREADY teal+orange+red+white** — Sir aapne shayad sochaa ki deep-blue hai, but actually theme already correct
- 🟡 **Per-component usage** — many components might use slate/indigo/emerald instead of brand vars; spot-audit needed
- 🟡 **AI Workflow Builder UI uses indigo gradient** (`from-indigo-500 to-purple-500` in some sections) — should swap to teal/orange

---

## 🅖 Pre-existing Collections (Mongo)

**Total: 119 collections.** Phase 20-relevant subset:

| Collection | Docs | Purpose | Need? |
|---|---|---|---|
| `products` | 19 | Product master | ✅ KEEP — add fields |
| `product_cost_structures` | 5 | Cost/commission templates | ✅ KEEP |
| `partner_product_commissions` | 1 | Per-partner overrides | ✅ KEEP |
| `pre_assessments` | 33 | PA records | ✅ KEEP |
| `pre_assessment_documents` | 13 | PA doc uploads | ✅ KEEP |
| `pre_assessment_reports_log` | 12 | Phase 19.11 PDF gen log | ✅ KEEP |
| `information_sheets` | 3 | Info Sheet data | ⚠️ MIGRATE schema |
| `eligibility_info_sheet_links` | 36 | Public fill links | ✅ KEEP |
| `client_eligibility_profiles` | 40 | Profile (Phase 6.7) | ✅ KEEP |
| `proposal_consent_emails` | 2 | Esign consent | ✅ KEEP |
| `workflow_steps` | 30 | Workflow step definitions | ✅ KEEP |
| `fee_country_catalog` | 20 | Country fee catalog | ✅ KEEP |
| `fee_estimates` | 2 | Saved estimates | ✅ KEEP |

**Collections NEEDED but MISSING:**
- ❌ `ai_workflow_templates` — verified templates currently live in code (`step_documents._find_best_template()`); should move to DB
- ❌ `pre_assessment_fees_policy` — per country/visa PA fee config (or use `products.base_fee`)
- ❌ `coupons` — discount codes (if Sir wants)
- ❌ `client_portals` — currently provisioning happens inline; no separate audit trail

---

# 📊 Reality-Adjusted Phase 20 Plan

Sir, audit ke baad **scope significantly smaller** ho gaya. Yahaan refined plan:

## 🟢 Phase 20.1 (~2 hr) — AI Workflow Builder Polish & Persistence
**Why first:** Sir's directive #1 (NO REMOVAL), and existing AI Workflow Builder is 90% there.
- Switch `_call_gpt` to **explicit Claude Sonnet 4.5** (Sir's directive #3) with fallback to GPT-5.2
- Add `vfsglobal.com/<country>` source URLs to `COUNTRY_REFERENCES` for each country
- Add `is_skill_assessment_required` rule: only AU/NZ PR workflows include skill assessment step
- Add **verified flag persistence**: `POST /api/ai-workflow/{workflow_id}/verify` writes `verified: true, verified_by, verified_at` to workflow record
- Migrate 10 verified templates from code → `ai_workflow_templates` collection
- Fix "AI service unavailable" UX: show retry button + degraded mode (template fallback) instead of error toast

## 🟢 Phase 20.2 (~2 hr) — Product Master Upgrade
- Add fields: `is_pre_assessment` (bool), `workflow_id` (FK), `visa_subclass`, `assessing_body_code`, `pre_assessment_fee_inr` (override; nullable)
- Add **category enum**: `pre_assessment | skill_assessment | visa_workflow | english_test | document_service | nomination | other`
- Soft-delete 11 TEST_ products (mark `status: archived`)
- Backfill country/visa_type from name pattern for legacy 7 real products
- Wire AI Workflow → Product `workflow_id` back-ref on save

## 🟢 Phase 20.3 (~2 hr) — Variable Pre-Assessment Fee (Sir's Q2)
- Remove `PRE_ASSESSMENT_FEE = 5100` hardcoded constant
- `create_pre_assessment` now requires `product_id` in payload → fetches `products.pre_assessment_fee_inr OR products.base_fee`
- Update Stripe checkout amount, `pa_fees_amount` field, all 4 endpoints (create, send-payment-link, mock-payment, confirm-payment)
- Backward compat: if `product_id` not provided, fallback to legacy 5100 with deprecation warning
- Frontend: PA create modal now requires product selection + shows live fee preview

## 🟢 Phase 20.4 (~3 hr) — Universal Info Sheet (Sir's spec)
- Migrate `information_sheets` collection from flat → 6-section nested schema (Sir's docx spec)
- Build new `<UniversalInfoSheet>` component with collapsible sections + dynamic multi-row tables (Family · Migrating Deps · Qualifications · Employment)
- **Reuse existing Claude Sonnet 4.6 resume extractor** → wire to new schema (map extracted fields to Personal + Employment + Qualifications sections)
- Single source of truth: Sales fills → CM edits same record → Audit trail preserved
- Backward compat: existing 3 records preserved + migrated

## 🟢 Phase 20.5 (~2 hr) — Funnel Stitching: PA → Admin Review → Proposal → Mini Portal
- New page `/admin/pre-assessment-pipeline` (already exists as `PreAssessmentPipeline.jsx` — upgrade)
- Lifecycle dashboard: shows each PA's status across the 7-stage funnel
- Single-click "Admin Review" → preview Phase 19.11 Report → edit if needed → "Generate Proposal" → "Send to Client" → tracks all in one record
- Client portal: dashboard showing Pre-Assessment Report download + Proposal + Info Sheet status

## 🟢 Phase 20.6 (~1 hr) — Brand Color Spot-Audit & Polish
- Audit components using indigo/purple/slate where teal/orange should be (mainly AIWorkflowBuilder hero, admin dashboards)
- Replace with `bg-primary`, `bg-secondary`, `bg-destructive` tokens to enforce brand consistency
- Polish AI Workflow Builder hero from indigo gradient → teal/orange gradient

## 🟡 Phase 20.7 (~1 hr) — Skill Assessment AU+NZ-only Rule
- AI prompt + verified templates: enforce skill_assessment step only when `country IN (AU, NZ) AND visa_subclass IN (189, 190, 491, NZ-SMC)`
- Frontend UI: conditional step rendering

## 🟡 Phase 20.8 (~1 hr) — Tests + Triple Gate + Documentation
- 25+ pytests across all phases
- Playwright screenshots for each major flow
- CHANGELOG + PRD update

**Total revised estimate: ~14 hr** (was Sir's 25-30 hr — **savings = ~50%** because so much already exists)

---

## ⚠️ Concerns & Blockers

1. **AI service stability** — `_call_gpt` raises on any LlmChat exception. If budget runs out mid-Phase 20.1 migration of 10 templates, we'll hit error. **Recommendation:** Add retry-with-backoff + fallback to GPT-5.2 if Claude fails.
2. **3 existing `information_sheets` records** — migration script needed; cannot lose data. **Recommendation:** Phase 19.6 import_batch + snapshot before migration.
3. **11 TEST_ products** — soft-delete vs hard-delete decision. **Recommendation:** Soft-delete (`status: archived`) so QA history preserved.
4. **VFSglobal URL pattern varies per country** — e.g. `vfsglobal.com/in/en/aus` vs `vfsglobal.com/en/uk/india` — need 1-time URL mapping table.
5. **Coupon system** — Sir didn't explicitly request, but mini portal flow may need it. **Decision needed.**

---

## 🎯 KEY QUESTIONS FOR SIR (please confirm before Phase 20.1 starts)

1. **Q1: AI model preference** — Sir, current setup defaults to LlmChat (likely Gemini/GPT). Should I wire **explicit Claude Sonnet 4.5** for AI Workflow generation (per directive #3), or keep GPT-5.2?
2. **Q2: Test products cleanup** — Soft-delete the 11 `TEST_` products (mark archived, hidden from sales)? Or hard-delete?
3. **Q3: Coupon system** — Add `coupons` collection + discount logic to PA fee? Or skip for now?
4. **Q4: Info Sheet migration** — Migrate 3 existing records to new 6-section schema (with backup), or start fresh?
5. **Q5: Phase order confirm** — Proposed sequence 20.1 → 20.6 → 20.2 → 20.3 → 20.4 → 20.5 → 20.7 → 20.8. Confirm or re-order?

---

**🛑 STOPPING HERE.** Sir, please review + answer Q1-Q5 above, then I'll begin **Phase 20.1**. No code touched yet.
