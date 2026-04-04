# LEAMSS Immigration Portal — PRD

## Original Problem Statement
Build a comprehensive immigration services portal (LEAMSS) with role-based dashboards for Admin, Case Manager, Partner, and Client. The portal handles sales tracking, case management, document processing, ticketing, commission tracking, and payment collection.

## Tech Stack
- **Frontend**: React, TailwindCSS, Shadcn UI
- **Backend**: FastAPI (Python), MongoDB (Motor async driver)
- **Auth**: JWT-based custom authentication
- **AI**: GPT-5.2 via emergentintegrations (Universal Key)
- **PDF**: reportlab for server-side PDF generation

## User Personas
- **Admin**: Full system access, user management, commission config, reports, analytics, workflow builder, marketing
- **Case Manager**: Case workflows, document review, ticket management, info sheets, AI document verification
- **Partner**: Sale booking (multi-currency), commission tracking, support tickets, referral codes
- **Client**: Case status, document upload/download, support tickets, info sheet view

## Core Requirements
1. Role-based authentication and dashboards
2. Sales management with multi-currency support (INR base)
3. Case workflow with step-by-step progression
4. Document management with upload/download/review
5. Ticketing system with real-time visibility
6. Commission tracking (global, per-partner, per-product)
7. Analytics dashboard with real data
8. Activity logging injected into business logic
9. Workflow Builder (drag-and-drop step reordering)
10. Marketing (referral codes + promo codes)
11. PDF report generation (sales, commission, partner sales)
12. AI Document Verification (GPT-5.2)
13. Notification system (mocked, no external APIs)
14. Mobile-responsive dashboards with collapsible sidebar
15. Email service integration (mocked to DB)

---

## What's Been Implemented

### Phase 1 — Core Features (DONE)
- [x] JWT auth with 4 roles (admin, case_manager, partner, client)
- [x] Admin Dashboard (users, products, cases, sales, tickets, refunds, analytics, settings)
- [x] Partner Dashboard (sales booking with currency selector, commissions, support)
- [x] Case Manager Dashboard (case management, document review, batch operations, info sheets)
- [x] Client Dashboard (case status, documents, tickets, info sheet view)
- [x] Global search, Activity log UI

### Phase 1 — Bug Fixes (DONE — April 3, 2026)
- [x] Document download, Date formatting, Ticket visibility
- [x] Client Information Sheet tab visibility
- [x] Ticket real-time filters, Product update saving
- [x] Analytics Dashboard data syncing
- [x] Sale currency display (INR base, no $ prefix on INR amounts)
- [x] Payment deadline timezone awareness fix

### Phase 1 — Advanced Features (DONE — April 3, 2026)
- [x] Per-partner per-product custom commission rates (CRUD API + Admin UI)
- [x] INR base currency with multi-currency support
- [x] Exchange rate configuration in settings
- [x] Commission calculation on `amount_received`
- [x] Mandatory ticket closure comments and rejection reasons
- [x] Refunds UI and backend logic
- [x] Payment Collection Tracker widget

### Phase A-D — New Features (DONE — April 4, 2026)
- [x] Workflow Builder (Admin page: select product, add/reorder/delete steps, save workflow)
- [x] Marketing Dashboard (Admin page: referral system + promo codes CRUD)
- [x] PDF Report Generation (Sales, Commission, Partner Sales — real PDF with reportlab)
- [x] AI Document Verification (GPT-5.2 via emergentintegrations Universal Key)
- [x] Activity Log injection into core business routers (sales, cases, documents, tickets)
- [x] Notification system (mocked — writes to DB, bell icon in UI)

### Mobile Responsiveness & Email Service (DONE — April 4, 2026)
- [x] Admin Dashboard: Collapsible sidebar with hamburger menu on mobile, responsive padding/grids
- [x] Partner Dashboard: Collapsible sidebar with hamburger menu on mobile
- [x] Case Manager Dashboard: Collapsible sidebar with hamburger menu on mobile
- [x] Client Dashboard: Responsive header (user name/CreateTicket hidden on small screens)
- [x] Email Service (MOCKED): Created email_service.py with 5 email functions
- [x] Wired emails into: Sale approval/rejection, Document review, Ticket replies, Case step updates
- [x] Email logs viewable at GET /api/activity/email-logs (admin only)
- [x] All 19 backend tests + all frontend tests passing (iteration 24)

---

## Prioritized Backlog

### P1 — Next
- [ ] CRM & Lead Management (lead pipeline, source tracking, follow-up reminders)
- [ ] Real email service integration (SendGrid/Resend — currently mocked)

### P2 — Planned
- [ ] Stripe Payment Gateway integration
- [ ] Bulk Document Upload UI improvements
- [ ] Activity Log page layout consistency (add admin sidebar wrapper)

### P3 — Future
- [ ] AI Chatbot for client queries
- [ ] SMS Notifications via Twilio
- [ ] Google Calendar integration for deadlines
- [ ] Standalone mobile apps (client + staff)

---

## Key API Endpoints
- `POST /api/auth/login` — JWT login
- `GET /api/sales`, `POST /api/sales` — Sales CRUD
- `GET /api/analytics/dashboard` — Analytics data
- `GET /api/workflows/{product_id}` — Get workflow steps
- `PUT /api/workflows/{product_id}` — Update workflow
- `GET /api/marketing/referral/stats` — Referral statistics
- `POST /api/marketing/promo` — Create promo code
- `GET /api/reports/export/sales-report` — PDF sales report
- `GET /api/reports/export/commission-report` — PDF commission report
- `POST /api/ai/verify-document/{doc_id}` — AI document verification
- `GET /api/activity/logs` — Activity audit logs
- `GET /api/activity/email-logs` — Email notification logs (admin only)
- `GET /api/notifications` — User notifications

## Database Collections (MongoDB)
`users`, `products`, `workflow_steps`, `sales`, `cases`, `case_steps`, `documents`, `tickets`, `ticket_messages`, `notifications`, `audit_logs`, `refunds`, `settings`, `partner_product_commissions`, `referrals`, `promo_codes`, `email_logs`
