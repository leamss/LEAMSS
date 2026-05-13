# LEAMSS — Roadmap (Prioritized Backlog)

> Last updated: Feb 13, 2026 (Phase 3B complete)

## 🟢 Currently Live
- ✅ Phases A-D: 5-step funnel
- ✅ Phase 1: RBAC Foundation
- ✅ Phase 2: Employee Portal
- ✅ Phase 2.2: Frontend Route Guards
- ✅ Phase 3A: Attendance & Leave Management
- ✅ **Phase 3B: HR Admin Settings UI** (5 admin pages + audit log)

---

## 🟡 P1 — Next Up

### Phase 3C — Attendance & Leave Reports / Exports
**Effort:** ~2-3 hours
- HR dashboard with dept-wise attendance %, monthly trends, top late comers
- CSV export: monthly attendance, leave balance ledger
- Manager analytics: subordinate punctuality, leave patterns
- Monthly attendance PDF report (per employee, printable)

### Phase 4 — Resend Live Emails Integration
- Need `RESEND_API_KEY` from user
- Wire to: leave decisions, regularization decisions, password reset, welcome email, HR escalation reminders

### Phase 5 — Real Stripe Payments Integration
- Test key available in pod environment
- Replace mocked /api/payments/* with real Stripe Checkout
- Auto invoice PDF generation on payment success

---

## 🟠 P2 — Backlog

- **Performance Module:** Goal-setting, 360 feedback, appraisal cycle
- **Edit History tab per PA:** UI for audit trail of edited PA fields
- **Biometric E-sign packet:** Capture device fingerprint, GPS, IP for legal disputes
- **Multi-location Office Support:** Different office hours per location
- **Shift management:** Night shift, rotating shifts
- **Comp-off auto-credit:** Auto-credit on holiday/weekend work
- **Half-day leave** support
- **Geo-Fencing:** Office IP / GPS lock for punch (UI placeholder exists)
- **Department-Head approval chain** (Phase 3B has flag, but DB-only — needs UI/router wiring)

---

## 🔵 P3 — Future

- Twilio WhatsApp full integration
- Progressive Web App (PWA) setup + Push notifications
- White-Label SaaS Architecture (multi-tenancy isolation)
- Payroll integration (LWP → salary deduction)
- Biometric / Face-recognition punch in
- Mobile app (React Native)
- AI-powered HR insights (predict attrition, leave abuse patterns) — Claude already wired

---

## 🔴 Known Limitations / Tech Debt

- `PRD.md` is 970+ lines — kept as static reference; live state in CHANGELOG/ROADMAP
- Babel `visual-edits` plugin sometimes throws stack overflow on huge JSX files. Mitigation: small components + React.lazy().
- LWP scanner runs on-demand (POST /api/attendance/lwp/scan) — should be cron-scheduled in production
- Sandwich leave only catches contiguous Fri-Mon / Sat-Mon ranges within a single request. Cross-request detection not implemented.
- All times stored as IST naive ISO strings. Centralized helper `core.attendance_logic.now_ist()`.
- Phase 3B "Department Head approval" toggle stored but workflow router has not been extended yet — flagged as P2.
