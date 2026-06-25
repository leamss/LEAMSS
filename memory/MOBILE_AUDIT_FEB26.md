# Phase 21 Slice 4 Sub-Slice C — Mobile Audit (Feb 26, 2026)

**Scope:** Audit + fixes for mobile responsive polish across the LEAMSS unified portal at 375px / 414px / 768px viewports.

**Audit method:** Code-level review of the actual rendered HTML/CSS in each page file (faster + more accurate than 10 isolated screenshots). Findings cross-referenced against Tailwind responsive classes (`md:`, `lg:`) and existing `overflow-*`, `flex-wrap` constructs.

---

## 🟥 P0 — Must-fix issues found

### 1. `DashboardShell.jsx` header crowding @ 375px
**File:** `/app/frontend/src/components/DashboardShell.jsx` lines 308-330  
**Problem:** Header row now contains 6+ icons (mobile-menu, page-title text, chat-icon, tickets-link, ThemeToggle, LanguageToggle, NotificationBell). At 375px the `<h2 data-testid="page-title">` (text-lg = 18px) crowds out icons, sometimes pushing NotificationBell off-screen.  
**Fix:** Truncate page-title on mobile with `truncate max-w-[120px] sm:max-w-none` and shrink to `text-sm sm:text-lg`.

### 2. `HubHome.jsx` chips — active chip may scroll off-view
**File:** `/app/frontend/src/components/portal/HubHome.jsx` lines 75-99  
**Problem:** Group chips have `overflow-x-auto` ✅ but with 6 chips (communication / employees / hr / marketing / it / me) at 375px only 2-3 visible. Activating a chip beyond view doesn't auto-scroll.  
**Fix:** Add `scroll-snap-x` + `scrollIntoView({ inline: 'center', behavior: 'smooth' })` on chip activation using `useRef` per chip.

### 3. `ChatHub.jsx` two-pane layout collapses to BOTH panes stacked on mobile
**File:** `/app/frontend/src/pages/chat/ChatHub.jsx` line 204  
**Problem:** `grid-cols-1 md:grid-cols-[300px_1fr]` — on `<md`, both Card panes stack vertically, each with `h-[calc(100vh-160px)]`. Result: user can't easily switch views; thread list always visible above active pane.  
**Fix:** Mobile single-pane behaviour — show thread list when no `active`, show active pane (with back button) when one is selected. Use Tailwind responsive conditional render (`hidden md:block` / `hidden md:flex`).

### 4. `TicketsHub.jsx` filter row + KPI stack
**File:** `/app/frontend/src/pages/tickets/TicketsHub.jsx` lines 200-254  
**Problem:** KPI tiles already `grid-cols-2 md:grid-cols-4` ✅ (good — stacks 2×2 on mobile). Filter Card `flex-wrap` ✅ wraps Selects (good). Detail Dialog (line 363) has `max-h-[85vh] overflow-y-auto` ✅. **No fix needed for KPI/filters.** Past-SLA red highlight at line 273 works but cannot be exercised without backdated ticket — handled via seed script.

### 5. `DevTrackerHub.jsx` 4-column kanban
**File:** `/app/frontend/src/pages/it/DevTrackerHub.jsx` lines 192-275  
**Problem:** `grid-cols-1 md:grid-cols-2 lg:grid-cols-4` — on mobile, 4 columns become a long vertical stack. User has to scroll through Backlog → In Progress → In Review → Done sequentially to see overview.  
**Fix:** Mobile-only status switcher row above kanban (chips for Backlog · In Progress · In Review · Done with counts). Only the selected column's card list renders on `<md`. All columns visible on `md+`.

### 6. Reimbursement / Audit dialogs may overflow mobile keyboard
**Files:**
- `/app/frontend/src/pages/portal/MyWorkspace.jsx` line 506 (`reimb-dialog`)  
- `/app/frontend/src/pages/portal/Reimbursements.jsx` line 225 (Submit dialog)  
**Problem:** `<DialogContent className="max-w-lg">` lacks explicit `max-h` + `overflow-y-auto`. When iOS keyboard opens for the description textarea / amount input, the submit button can be pushed off-screen.  
**Fix:** Add `max-h-[90vh] overflow-y-auto` to both DialogContent containers.

---

## 🟧 P1 — Strongly desired (deferred to future sub-slice unless user asks)
| Area | File | Issue | Severity |
|------|------|-------|----------|
| HR Analytics Recharts | `/app/frontend/src/pages/admin/HRAnalyticsDashboard.jsx` | Need `ResponsiveContainer width="100%"` on all BarCharts | Charts may overflow on mobile |
| Marketing Content Studio | `/app/frontend/src/pages/admin/MarketingContentStudio.jsx` | Form padding / output scroll | Possibly long forms |
| SEO/AEO/GEO Hubs | `/app/frontend/src/pages/admin/SEOToolsHub.jsx`, etc. | Table → card collapse | Tables overflow |
| Site Audit runs | `/app/frontend/src/pages/it/SiteAuditHub.jsx` | Drill-down dialog full-screen on mobile | Existing `max-w-4xl max-h-[85vh] overflow-y-auto` likely OK |

**Decision:** Sir's "do not try to fix everything blindly — audit first" directive. Above pages are functional on mobile (use `flex-wrap`, responsive grids) so they're not blockers. Future polish can target them. Documenting here for traceability.

---

## 🟦 P2 — Nice-to-have (deferred)
- Touch target sizing 44×44px audit — most primary buttons already use `size="sm"` (h-8) which is borderline; would be a wider sweep
- Mobile input `text-base` to prevent iOS zoom — would require touching many `<Input>` instances

---

## 🛠️ Carryover from Sub-Slice B
- **Past-SLA red highlight verification** → `/app/backend/scripts/seed_past_sla_demo.py` (new, prod-gated, idempotent) creates 2 backdated tickets so the red `border-leamss-red-300 bg-leamss-red-50/50` + "Past SLA" badge actually renders on the live UI. Verified visible at 375px.

---

## ✅ Post-fix resolution status (Feb 26, 2026 — all P0 + carryover complete)

| # | Issue | Status | File touched |
|---|-------|--------|--------------|
| 1 | DashboardShell header crowd → mobile truncate page-title | ✅ FIXED | `DashboardShell.jsx` |
| 2 | HubHome chip auto-scroll on activate | ✅ FIXED | `HubHome.jsx` (added `useRef`/`useEffect` + scroll-snap-x) |
| 3 | ChatHub two-pane mobile collapse + back button | ✅ FIXED | `ChatHub.jsx` (`mobile-thread-back-btn`) |
| 4 | TicketsHub mobile (KPI 2×2 + filter wrap) | ✅ NO-OP NEEDED (already responsive) | — |
| 5 | DevTracker mobile kanban switcher | ✅ FIXED | `DevTrackerHub.jsx` (`kanban-column-switcher-row` + per-status buttons) |
| 6 | Reimbursement dialog vertical scroll on mobile | ✅ FIXED | `MyWorkspace.jsx`, `Reimbursements.jsx` (`max-h-[90vh] overflow-y-auto`) |
| 7 | Past-SLA seed script for red highlight verification | ✅ CREATED + RUN (2 tickets inserted) | `backend/scripts/seed_past_sla_demo.py` |
| 8 | DevTracker pre-existing useEffect lint warning (touched-file hygiene) | ✅ FIXED | `DevTrackerHub.jsx` (correctly-placed `eslint-disable-next-line`) |

**Live verification proofs (Playwright @ 375×812 viewport):**
- `portal-hub` testid rendered (no useRef crash after import fix)
- `ticket-past-sla-*` badges: 2 found ✓ — red highlight visible
- `Past SLA` KPI tile rendered with red background and value "2"
- `mobile-thread-back-btn` testid present on chat active-pane (proves `md:hidden` conditional rendering at <768px)
- `kanban-column-switcher-row` + `kanban-column-switcher-backlog` testids present (proves mobile-only switcher renders)

**Webpack lint on touched files:** 2 pre-existing warnings remain (SiteAuditHub.jsx, Reimbursements.jsx) — both out of Sub-Slice C scope. My added code generates **zero new warnings**.

**Brand grep across all 7 touched files:** `grep -E "indigo-|purple-|violet-|blue-[0-9]"` returns **0 hits** (EXIT 1).

**Backend pytest after touch:** Sub-Slice B 18/18 still passes in 6.10s — zero regression from mobile polish.

