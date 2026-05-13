# LEAMSS — Roadmap (Prioritized Backlog)

> Last updated: Feb 13, 2026

## 🟢 Currently Live
- ✅ Phases A-D: 5-step funnel (Pre-Assessment → AI Proposal → E-sign → Payment → Case Manager)
- ✅ Phase 1: RBAC Foundation (18 roles, 8 depts, 219 perms)
- ✅ Phase 2: Employee Portal (Dashboard, Departments, Org Chart, Password Reset, Role History)
- ✅ Phase 2.2: Frontend Route Guards
- ✅ Phase 3A: Attendance & Leave Management (full company policies)

---

## 🟡 P1 — Next Up

### Phase 3B — HR Admin Settings UI (Frontend for hr_admin endpoints)
**Effort:** ~2-3 hours
**Pages to build:**
- `/admin/hr/settings` — Edit attendance_settings (office hours, late threshold, monthly cap, sandwich toggle, etc.)
- `/admin/hr/holidays` — Holiday calendar manager (add/remove/edit)
- `/admin/hr/leave-types` — Edit annual quotas, monthly caps per leave type
- `/admin/hr/approver-config` — Set final approver, dept-wise approvers, backup approver
- Backend already exists at `routers/hr_admin.py`

### Phase 3C — Attendance & Leave Reports / Exports
- HR dashboard with dept-wise attendance %, monthly trends, top late comers
- CSV export: monthly attendance, leave balance ledger
- Manager analytics: subordinate punctuality, leave patterns

### Phase 4 — Resend Live Emails Integration
- Need `RESEND_API_KEY` from user
- Wire to: leave decisions, regularization decisions, password reset, welcome email

### Phase 5 — Real Stripe Payments Integration
- Test key available in pod environment
- Replace mocked /api/payments/* with real Stripe Checkout
- Auto invoice PDF generation on payment success

---

## 🟠 P2 — Backlog

- **Performance Module:** Goal-setting, 360 feedback, appraisal cycle (separate from payroll)
- **Edit History tab per PA:** UI for audit trail of edited PA fields
- **Biometric E-sign packet:** Capture device fingerprint, GPS, IP for legal disputes
- **Multi-location Office Support:** Different office hours per location (e.g., Mumbai vs Bangalore)
- **Shift management:** Night shift, rotating shifts with different timings
- **Comp-off auto-credit:** When employee punches in on holiday/weekend, auto-credit comp-off
- **Half-day leave** support (currently only full days)

---

## 🔵 P3 — Future

- Twilio WhatsApp full integration (currently mocked)
- Progressive Web App (PWA) setup + Push notifications
- White-Label SaaS Architecture (multi-tenancy isolation)
- Payroll integration (salary deduction for LWP, late marks)
- Biometric / Face-recognition punch in
- Mobile app (React Native)
- AI-powered HR insights (predict attrition, leave abuse patterns)

---

## 🔴 Known Limitations / Tech Debt

- `PRD.md` is 949+ lines — could be split further per persona/module
- Babel `visual-edits` plugin sometimes throws `Maximum call stack size exceeded` for files with many conditional JSX returns. Workaround: use React.lazy() + small components.
- LWP scanner runs on-demand (POST /api/attendance/lwp/scan) — should be cron-scheduled in production
- Sandwich leave only catches contiguous Fri-Mon / Sat-Mon ranges. Two separate leave requests for Fri-only + Mon-only are not cross-validated.
- All times stored as IST naive ISO strings in DB. UTC conversion logic centralized in `core/attendance_logic.now_ist()` but could benefit from a dedicated timezone helper.
