# LEAMSS — Roadmap (Prioritized Backlog)

> Last updated: Feb 13, 2026 (Phase 4A foundation complete)

## 🟢 Currently Live
- ✅ Phases A-D: 5-step funnel
- ✅ Phase 1: RBAC Foundation
- ✅ Phase 2: Employee Portal
- ✅ Phase 2.2: Frontend Route Guards
- ✅ Phase 3A: Attendance & Leave Management
- ✅ Phase 3B: HR Admin Settings UI
- ✅ **Phase 4A: Sales Workflow Inheritance** (Sales execs = internal partners)

---

## 🟡 P1 — Next Up

### Phase 4B — Targets Management
**Effort:** ~2-3 hours
- New `targets` collection (per-user, per-period: monthly/quarterly/yearly)
- Admin sets targets (individual or bulk)
- Live progress calculation from PAs
- Visual progress bars + milestone notifications
- TargetWidget on `/sales/dashboard` wires to real data

### Phase 4C — Commission Engine
**Effort:** ~3-4 hours
- Configurable commission slabs per role (e.g., 3%/5%/7%/10%)
- Auto-calculate on PA close (`status=case_created`)
- Bonus/deduction/TDS rules
- 2-stage approval workflow (Manager → HR → Paid)
- CommissionWidget wires to real data

### Phase 4D — Call Log & Activity
- Log every client touchpoint linked to PAs
- Schedule follow-ups (due_date, notification)
- Quick "Log Call" action button on PA detail
- FollowupsWidget on dashboard wires to real data

### Phase 4E — Leaderboard & Reports
- Monthly/quarterly leaderboards (top performers)
- Department-wide reports for managers/heads
- CSV exports
- TeamRankWidget wires to real data

### Phase 4F — Manager / Head Views (Deferred from 4A)
- `/sales/team-dashboard` for sales_manager (reports_to + team_id scope)
- `/sales/dept-dashboard` for sales_head (department scope)
- Approvals inbox (discount approvals)

### Phase 5 — Resend Live Emails Integration
- Need `RESEND_API_KEY`

### Phase 6 — Real Stripe Payments Integration
- Test key in pod

### 🇨🇦 Phase 10 Series — Canada Atlas (in progress)
- ✅ **Phase 10.1** — NOC 2021 V1.0 Bulk Importer (516 unit groups, June 8 2026)
- 🟢 **Phase 10.2** — IRCC Express Entry Streams Mapping (FSWP/CEC/FSTP + 10 categories) — Next
- 🟢 **Phase 10.3** — 11 PNP Provincial Nomination Scrapers (BC/ON/AB/SK/MB/NB/NS/PE/NL/YT/NT)
  - **🌟 Enhancement to ship with 10.3:** AI Auto-Suggest — client says "I'm a baker, want to go to Quebec" → system auto-suggests NOC 63201 + tags Quebec PEQ stream + shows IRCC EE eligibility + provincial draws in 2 seconds (Sonnet 4.6 hybrid Haiku 4.5 router)
- 🟢 **Phase 10.4** — IRCC Round Cutoff Tracker (CRS min scores per category)
- 🟢 **Phase 10.5** — AIP + RNIP Regional Programs (AU DAMA/ILA equivalent)
- 🟢 **Phase 10.6** — Atlas Verify Card + Calculator Rules for CA

---

## 🟠 P2 — Backlog

- **Bulk Auto-Verify Tool for Occupation Master**: One-click bulk verification with auto source-attribution per data source. Currently only 4/932 AU codes verified — UI tool needed to verify ~888 codes that came from scrapers in one click (with auto source URL from scraper origin). 3 plans available: A) Bulk by source, B) Top-100 priority queue, C) Self-audit one-by-one.
- **Phase 3C — Reports/Exports**: HR dashboard, dept-wise attendance %, monthly PDFs
- **Performance Module**: Goal-setting, 360 feedback
- **Edit History tab per PA**
- **Biometric E-sign packet**: device fingerprint, GPS, IP for legal disputes
- **Multi-location Office Support**: per-location office hours
- **Shift management**: Night shift, rotating shifts
- **Comp-off auto-credit** on holiday/weekend work
- **Half-day leave** support
- **Geo-Fencing**: Office IP/GPS lock for punch
- **Refactor `pre_assessment.py`**: 950+ lines — split into `pa_create.py`, `pa_payment.py`, `pa_documents.py`, `pa_proposal.py`, etc.
- **Apply `_assert_pa_owner` everywhere**: 6 other PA-scoped endpoints still inline the ownership check

---

## 🔵 P3 — Future

- Twilio WhatsApp full integration
- Progressive Web App (PWA) setup + Push notifications
- White-Label SaaS Architecture
- Payroll integration (LWP → salary deduction)
- Biometric / Face-recognition punch in
- Mobile app (React Native)
- AI-powered HR insights (predict attrition, leave abuse) — Claude already wired

---

## 🔴 Known Limitations / Tech Debt

- `PRD.md` is 970+ lines — kept as static reference
- Babel `visual-edits` plugin can stack-overflow on huge JSX files — keep components small
- LWP scanner runs on-demand only — needs cron in production
- Sandwich leave catches only contiguous Fri-Mon/Sat-Mon within single request
- `pre_assessment.py` reaching 950+ lines — refactor recommended for Phase 4 follow-ups
- 6 PA endpoints still have inline ownership checks instead of using the new `_assert_pa_owner` helper
